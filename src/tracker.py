"""Identity lock and position tracking for one enrolled person.

Coordinate mapping lives here: error_x = (face_center_x - W/2) / (W/2), from the real frame size.
"""

import logging
from dataclasses import dataclass
from enum import Enum, auto

import numpy as np

from .haar_5pt import align_face_5pt

logger = logging.getLogger(__name__)


class LockState(Enum):
    SEARCHING = auto()
    LOCKED = auto()
    LOST = auto()


def iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1, (bx2 - bx1) * (by2 - by1))
    return inter / float(area_a + area_b - inter)


def center(box):
    x1, y1, x2, y2 = box
    return np.array([(x1 + x2) / 2.0, (y1 + y2) / 2.0], dtype=np.float32)


@dataclass
class TrackingSignal:
    error_x: float
    error_y: float
    horizontal: str
    vertical: str


class LockedFaceTracker:
    def __init__(
        self,
        target_name: str,
        detector,
        embedder,
        matcher,
        verify_every: int = 10,
        lost_timeout: int = 24,
        ema_alpha: float = 0.30,
        dead_zone: float = 0.05,
    ):
        self.target_name = target_name
        self.detector = detector
        self.embedder = embedder
        self.matcher = matcher
        self.verify_every = verify_every
        self.lost_timeout = lost_timeout
        self.ema_alpha = ema_alpha
        self.dead_zone = dead_zone
        self.state = LockState.SEARCHING
        self.last_box = None
        self.smooth_center = None
        self.lost_frames = 0
        self.frame_index = 0

    @staticmethod
    def box(face):
        return (face.x1, face.y1, face.x2, face.y2)

    def identity(self, frame, face):
        aligned, _ = align_face_5pt(frame, face.kps, out_size=(112, 112))
        return self.matcher.match(self.embedder.embed(aligned))

    def target_is_verified(self, frame, face) -> bool:
        match = self.identity(frame, face)
        return match.accepted and match.name == self.target_name

    def acquire(self, frame, faces):
        best = None
        best_similarity = -1.0
        for face in faces:
            match = self.identity(frame, face)
            logger.debug(
                "acquire: candidate box=%s matched=%r similarity=%.3f distance=%.3f accepted=%s",
                self.box(face), match.name, match.similarity, match.distance, match.accepted,
            )
            if (
                match.accepted
                and match.name == self.target_name
                and match.similarity > best_similarity
            ):
                best, best_similarity = face, match.similarity
        if best is not None:
            logger.info(
                "acquired target %r at box=%s similarity=%.3f",
                self.target_name, self.box(best), best_similarity,
            )
        return best

    def associate(self, faces):
        if self.last_box is None or not faces:
            return None

        # with only one face in view there's nothing to disambiguate against -
        # a fast-moving target can outrun the displacement penalty below and
        # get wrongly rejected even though it's obviously still the same
        # (only) face, so skip straight to it and let periodic ArcFace
        # re-verification catch a genuine handoff to someone else
        if len(faces) == 1:
            logger.debug("associate: single face in view, skipping displacement scoring")
            return faces[0]

        last_center = center(self.last_box)
        last_diag = max(np.linalg.norm(
            np.array([self.last_box[2] - self.last_box[0],
                      self.last_box[3] - self.last_box[1]], dtype=np.float32)
        ), 1.0)
        ranked = []
        for face in faces:
            box = self.box(face)
            overlap = iou(self.last_box, box)
            displacement = np.linalg.norm(center(box) - last_center) / last_diag
            score = overlap - 0.20 * displacement
            ranked.append((score, face))
        score, candidate = max(ranked, key=lambda item: item[0])
        chosen = candidate if score > -0.45 else None
        logger.debug(
            "associate: best_score=%.3f box=%s -> %s",
            score, self.box(candidate), "kept" if chosen is not None else "rejected",
        )
        return chosen

    def update(self, frame):
        self.frame_index += 1
        faces = self.detector.detect(frame, max_faces=8)
        logger.debug("frame=%d state=%s faces_detected=%d", self.frame_index, self.state.name, len(faces))

        if self.state == LockState.SEARCHING:
            candidate = self.acquire(frame, faces)
        else:
            candidate = self.associate(faces)
            due_for_verify = self.state == LockState.LOST or self.frame_index % self.verify_every == 0
            if candidate is not None and due_for_verify:
                verified = self.target_is_verified(frame, candidate)
                logger.debug("periodic re-verification: verified=%s", verified)
                if not verified:
                    candidate = None

        if candidate is None:
            self.lost_frames += 1
            if self.last_box is not None and self.state != LockState.LOST:
                logger.info("target %r LOST (frame=%d, was at %s)", self.target_name, self.frame_index, self.last_box)
            if self.last_box is not None:
                self.state = LockState.LOST
            if self.lost_frames > self.lost_timeout:
                if self.state == LockState.LOST:
                    logger.info(
                        "target %r missing for %d frames (> lost_timeout=%d) -> back to SEARCHING",
                        self.target_name, self.lost_frames, self.lost_timeout,
                    )
                self.state = LockState.SEARCHING
                self.last_box = None
                self.smooth_center = None
            return None, None

        if self.state != LockState.LOCKED:
            logger.info("target %r LOCKED (frame=%d)", self.target_name, self.frame_index)
        self.state = LockState.LOCKED
        self.lost_frames = 0
        self.last_box = self.box(candidate)
        raw_center = center(self.last_box)

        if self.smooth_center is None:
            self.smooth_center = raw_center
        else:
            a = self.ema_alpha
            self.smooth_center = a * raw_center + (1.0 - a) * self.smooth_center
        signal = self.position_signal(frame.shape)
        logger.debug(
            "position: raw_center=%s smoothed=%s error=(%.3f,%.3f) H=%s V=%s",
            raw_center, self.smooth_center, signal.error_x, signal.error_y,
            signal.horizontal, signal.vertical,
        )
        return candidate, signal

    def position_signal(self, shape) -> TrackingSignal:
        height, width = shape[:2]
        ex = float((self.smooth_center[0] - width / 2.0) / (width / 2.0))
        ey = float((self.smooth_center[1] - height / 2.0) / (height / 2.0))
        horizontal = "CENTER"
        vertical = "CENTER"
        if ex < -self.dead_zone:
            horizontal = "LEFT"
        elif ex > self.dead_zone:
            horizontal = "RIGHT"
        if ey < -self.dead_zone:
            vertical = "UP"
        elif ey > self.dead_zone:
            vertical = "DOWN"
        return TrackingSignal(ex, ey, horizontal, vertical)
