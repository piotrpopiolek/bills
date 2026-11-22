"""Import every mapped class so SQLAlchemy can configure relationships."""

import src.auth.models  # noqa: F401
import src.bill_items.models  # noqa: F401
import src.bills.models  # noqa: F401
import src.categories.models  # noqa: F401
import src.product_candidates.models  # noqa: F401
import src.product_index_aliases.models  # noqa: F401
import src.product_indexes.models  # noqa: F401
import src.shops.models  # noqa: F401
import src.telegram_messages.models  # noqa: F401
import src.users.models  # noqa: F401
