"""A renamed line keeps an alias. An unchanged name does not."""

from types import SimpleNamespace

import pytest

from src.bills.correction import ReceiptCorrection, alias_for_rename, names_differ


def test_same_name_does_not_write_an_alias() -> None:
    assert names_differ("Mleko", " mleko ") is False
    assert alias_for_rename("MLEKO UHT", "Mleko", "mleko") is None


def test_a_rename_aliases_the_receipt_wording() -> None:
    assert alias_for_rename("MLEKO UHT", "Mleko", "mleko 3.2%") == "MLEKO UHT"


def test_a_rename_without_ocr_text_aliases_the_previous_name() -> None:
    assert alias_for_rename(None, "Mleko", "mleko 3.2%") == "Mleko"


class _Session:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def get(self, _model: object, _key: int) -> SimpleNamespace:
        return SimpleNamespace(user_id=4, shop_id=2)

    async def scalar(self, _stmt: object) -> SimpleNamespace:
        return SimpleNamespace(
            id=9,
            bill_id=1,
            category_id=3,
            original_text="MLEKO UHT",
            index=SimpleNamespace(name="Mleko"),
        )

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def _correction(
    session: _Session, *, fail_item: bool
) -> tuple[ReceiptCorrection, list[bool]]:
    flags: list[bool] = []
    correction = ReceiptCorrection(session)  # type: ignore[arg-type]
    item = SimpleNamespace(
        id=9,
        bill_id=1,
        category_id=3,
        original_text="MLEKO UHT",
        index=SimpleNamespace(name="Mleko"),
    )

    async def owned_item(
        _bill_id: int, _item_id: int, _user_id: int
    ) -> SimpleNamespace:
        return item

    async def owned_bill(_bill_id: int, _user_id: int) -> SimpleNamespace:
        return SimpleNamespace(user_id=4, shop_id=2)

    correction._owned_item = owned_item  # type: ignore[method-assign]
    correction._owned_bill = owned_bill  # type: ignore[method-assign]

    async def create_or_get_existing(
        _data: object, *, commit: bool = True
    ) -> SimpleNamespace:
        flags.append(commit)
        return SimpleNamespace(id=7)

    async def upsert_alias(**kwargs: object) -> None:
        flags.append(bool(kwargs["commit"]))

    async def update(*_args: object, commit: bool = True, **_kwargs: object) -> str:
        flags.append(commit)
        if fail_item:
            raise RuntimeError("zapis pozycji")
        return "saved"

    correction.indexes.create_or_get_existing = create_or_get_existing  # type: ignore[method-assign]
    correction.aliases.upsert_alias = upsert_alias  # type: ignore[method-assign]
    correction.items.update = update  # type: ignore[method-assign]
    return correction, flags


async def test_a_rename_commits_the_catalog_with_the_item() -> None:
    session = _Session()
    correction, flags = _correction(session, fail_item=False)

    saved = await correction.save_item(
        bill_id=1,
        item_id=9,
        user_id=4,
        name="mleko 3.2%",
        quantity=None,
        unit_price=None,
        total_price=None,
    )

    assert saved == "saved"
    assert flags == [False, False, False]
    assert session.commits == 1
    assert session.rollbacks == 0


async def test_a_failed_item_save_rolls_back_the_rename() -> None:
    session = _Session()
    correction, flags = _correction(session, fail_item=True)

    with pytest.raises(RuntimeError, match="zapis pozycji"):
        await correction.save_item(
            bill_id=1,
            item_id=9,
            user_id=4,
            name="mleko 3.2%",
            quantity=None,
            unit_price=None,
            total_price=None,
        )

    assert flags == [False, False, False]
    assert session.commits == 0
    assert session.rollbacks == 1
