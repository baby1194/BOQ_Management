from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import models
from services.project_info_copy import copy_project_info


def _session():
    engine = create_engine("sqlite://")
    models.Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_copy_project_info_writes_header_and_concentration_sheets():
    source = _session()
    source.add(
        models.ProjectInfo(
            project_name="Tower A",
            project_name_hebrew="מגדל א",
            main_contractor_name="Main Co",
            subcontractor_name="Sub Co",
            developer_name="Dev Co",
            contract_no="C-12",
            invoice_no_submitted_qty="INV-1",
            invoice_date_submitted_qty=datetime(2026, 1, 2, tzinfo=timezone.utc),
            invoice_no_approved_signed_qty="INV-2",
            invoice_date_approved_signed_qty=datetime(2026, 2, 3, tzinfo=timezone.utc),
        )
    )
    source.commit()

    target = _session()
    item = models.BOQItem(
        display_order=0,
        section_number="01.01",
        description="Item",
        unit="m",
        original_contract_quantity=1,
        price=1,
        total_contract_sum=1,
    )
    target.add(item)
    target.flush()
    target.add(
        models.ConcentrationSheet(
            boq_item_id=item.id,
            sheet_name="Concentration Sheet - 01.01",
        )
    )
    target.commit()

    assert copy_project_info(source, target) is True
    target.commit()

    copied = target.query(models.ProjectInfo).one()
    assert copied.project_name == "Tower A"
    assert copied.project_name_hebrew == "מגדל א"
    assert copied.main_contractor_name == "Main Co"
    assert copied.subcontractor_name == "Sub Co"
    assert copied.developer_name == "Dev Co"
    assert copied.contract_no == "C-12"
    assert copied.invoice_no_submitted_qty == "INV-1"
    assert copied.invoice_no_approved_signed_qty == "INV-2"

    sheet = target.query(models.ConcentrationSheet).one()
    assert sheet.project_name == "Tower A"
    assert sheet.contractor_in_charge == "Main Co"
    assert sheet.contract_no == "C-12"
    assert sheet.developer_name == "Dev Co"


def test_copy_project_info_does_nothing_when_source_is_empty():
    source = _session()
    target = _session()

    assert copy_project_info(source, target) is False
    target.commit()
    assert target.query(models.ProjectInfo).count() == 0
