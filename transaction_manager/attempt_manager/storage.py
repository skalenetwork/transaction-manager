#   -*- coding: utf-8 -*-
#
#   This file is part of SKALE Transaction Manager
#
#   Copyright (C) 2021 SKALE Labs
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.


from abc import ABCMeta, abstractmethod
from typing import Optional

from ..structures import Attempt
from ..resources import rs as grs, redis


class BaseAttemptStorage(metaclass=ABCMeta):
    @abstractmethod
    def get(self) -> Optional[Attempt]:  # pragma: no cover
        pass

    def save(self, attempt: Attempt) -> None:  # pragma: no cover
        pass


class RedisAttemptStorage(BaseAttemptStorage):
    def __init__(self, rs: redis.Redis = grs) -> None:
        self.rs = rs

    def get(self) -> Optional[Attempt]:
        attempt_bytes = self.rs.get(b'last_attempt')
        if not attempt_bytes:
            return None
        return Attempt.from_bytes(attempt_bytes)

    def save(self, attempt: Attempt) -> None:
        self.rs.set(b'last_attempt', attempt.to_bytes())
