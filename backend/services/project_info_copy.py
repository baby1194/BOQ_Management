"""Copy the project-info header from one project database into another."""

from sqlalchemy.orm import Session

from models import models

PROJECT_INFO_FIELDS = (
    "project_name",
    "project_name_hebrew",
    "main_contractor_name",
    "subcontractor_name",
    "developer_name",
    "contract_no",
    "invoice_no_submitted_qty",
    "invoice_date_submitted_qty",
    "invoice_no_approved_signed_qty",
    "invoice_date_approved_signed_qty",
)


def copy_project_info(source: Session, target: Session) -> bool:
    """Copy project info onto the target. Returns False when the source has none.

    Concentration sheets already in the target get the same header fields
    that a project-info save writes onto them.
    """
    source_info = source.query(models.ProjectInfo).first()
    if source_info is None:
        return False

    target_info = target.query(models.ProjectInfo).first()
    if target_info is None:
        target_info = models.ProjectInfo()
        target.add(target_info)

    for field in PROJECT_INFO_FIELDS:
        setattr(target_info, field, getattr(source_info, field))

    for sheet in target.query(models.ConcentrationSheet).all():
        if target_info.project_name:
            sheet.project_name = target_info.project_name
        if target_info.main_contractor_name:
            sheet.contractor_in_charge = target_info.main_contractor_name
        if target_info.contract_no:
            sheet.contract_no = target_info.contract_no
        if target_info.developer_name:
            sheet.developer_name = target_info.developer_name

    return True
