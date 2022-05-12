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

import logging
from abc import ABCMeta, abstractmethod
from functools import wraps
from typing import Any, Callable, cast, Optional, TypeVar

from ..structures import Attempt, Tx

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


class NoCurrentAttemptError(Exception):
    pass


def made(func: F) -> F:
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.current:
            return func(self, *args, **kwargs)
        else:
            raise NoCurrentAttemptError('Current attempt is not set')
    return cast(F, wrapper)


class BaseAttemptManager(metaclass=ABCMeta):
    @property
    @abstractmethod
    def current(self) -> Optional[Attempt]:  # pragma: no cover
        pass

    @abstractmethod
    def fetch(self) -> None:  # pragma: no cover
        pass

    @abstractmethod
    def save(self) -> None:  # pragma: no cover
        pass

    @abstractmethod
    def make(self, tx: Tx) -> None:  # pragma: no cover
        pass

    @abstractmethod
    def replace(self, tx: Tx, replace_attempt: int) -> None:  # pragma: no cover
        pass
