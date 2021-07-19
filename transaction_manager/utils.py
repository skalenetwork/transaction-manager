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

from typing import Dict


def is_constant(var: str) -> bool:
    return len(var) > 0 and var[0].isupper() and var[-1].isupper()


def config_string(config_vars: Dict) -> str:
    return '\n'.join(
        f'{k}: {v}'
        for k, v in config_vars.items()
        if is_constant(k) and isinstance(v, (int, float, str, list))
    )
