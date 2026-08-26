"""WebUI environment snapshots.

The package facade preserves the former ``base_manager.snapshot`` public API;
implementation details are grouped by responsibility in sibling modules.
"""

from .codec import *  # noqa: F401,F403
from .collection import *  # noqa: F401,F403
from .io import *  # noqa: F401,F403
from .models import *  # noqa: F401,F403
from .storage import *  # noqa: F401,F403
