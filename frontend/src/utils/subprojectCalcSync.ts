import { askYesNo } from "../components/YesNoDialog";
import { calculationSheetsApi } from "../services/api";
import { SubprojectCalcUpdate } from "../types";
import { formatNumber } from "./format";

type Translate = (key: string, options?: Record<string, unknown>) => string;

function showPrice(value: number | null | undefined): string {
  if (value == null) return "—";
  return formatNumber(value, 2);
}

function quantityLines(updates: SubprojectCalcUpdate[], t: Translate): string {
  return updates
    .map((item) => {
      const line = t("calculationSheets.subprojectQtyLine", {
        section: item.section_number,
        sheet: item.calculation_sheet_no,
        project: item.project_name,
        oldEstimated: formatNumber(item.old_estimated_quantity),
        newEstimated: formatNumber(item.new_estimated_quantity),
        oldSubmitted: formatNumber(item.old_quantity_submitted),
        newSubmitted: formatNumber(item.new_quantity_submitted),
      });
      const sameNumbers =
        item.old_estimated_quantity === item.new_estimated_quantity &&
        item.old_quantity_submitted === item.new_quantity_submitted;
      if (item.details_changed && sameNumbers) {
        return `${line}\n${t("calculationSheets.subprojectQtyDetails")}`;
      }
      return line;
    })
    .join("\n\n");
}

function priceLines(updates: SubprojectCalcUpdate[], t: Translate): string {
  return updates
    .map((item) =>
      t("calculationSheets.subprojectPriceLine", {
        section: item.section_number,
        sheet: item.calculation_sheet_no,
        project: item.project_name,
        oldPrice: showPrice(item.old_price),
        newPrice: showPrice(item.new_price),
      })
    )
    .join("\n\n");
}

type Choice = {
  project_id: string;
  calculation_sheet_no: string;
  previous_calculation_sheet_no: string;
  section_number: string;
  update_quantity: boolean;
  update_price: boolean;
};

function sameChoice(choice: Choice, item: SubprojectCalcUpdate): boolean {
  return (
    choice.project_id === item.project_id &&
    choice.calculation_sheet_no === item.calculation_sheet_no &&
    choice.section_number === item.section_number
  );
}

/** Ask, separately, whether a quantity change and a price change should follow into the sub-project. */
export async function offerSubprojectCalcUpdates(
  updates: SubprojectCalcUpdate[] | undefined,
  t: Translate
): Promise<void> {
  if (!updates || updates.length === 0) return;

  const quantity = updates.filter((item) => item.quantity_changed);
  const price = updates.filter((item) => item.price_changed);
  const choices: Choice[] = [];

  if (
    quantity.length > 0 &&
    (await askYesNo(
      t("calculationSheets.subprojectQtyPrompt", {
        lines: quantityLines(quantity, t),
      })
    ))
  ) {
    for (const item of quantity) {
      choices.push({
        project_id: item.project_id,
        calculation_sheet_no: item.calculation_sheet_no,
        previous_calculation_sheet_no: item.previous_calculation_sheet_no,
        section_number: item.section_number,
        update_quantity: true,
        update_price: false,
      });
    }
  }

  if (
    price.length > 0 &&
    (await askYesNo(
      t("calculationSheets.subprojectPricePrompt", {
        lines: priceLines(price, t),
      })
    ))
  ) {
    for (const item of price) {
      const existing = choices.find((choice) => sameChoice(choice, item));
      if (existing) {
        existing.update_price = true;
      } else {
        choices.push({
          project_id: item.project_id,
          calculation_sheet_no: item.calculation_sheet_no,
          previous_calculation_sheet_no: item.previous_calculation_sheet_no,
          section_number: item.section_number,
          update_quantity: false,
          update_price: true,
        });
      }
    }
  }

  if (choices.length === 0) return;

  try {
    const result = await calculationSheetsApi.applySubprojectUpdates(choices);
    const summary = t("calculationSheets.subprojectUpdated", {
      count: result.updated,
    });
    if (result.errors && result.errors.length > 0) {
      window.alert(`${summary}\n\n${result.errors.join("\n")}`);
    } else {
      window.alert(summary);
    }
  } catch (err) {
    console.error("Error updating the sub-project calculation sheet:", err);
    window.alert(t("calculationSheets.subprojectApplyFailed"));
  }
}

/** True when the user also wants the same calculation sheet removed from the sub-project. */
export async function askDeleteSubprojectSheets(
  sheetIds: number[],
  t: Translate
): Promise<boolean> {
  if (sheetIds.length === 0) return false;
  try {
    const copies = await calculationSheetsApi.subprojectCopies(sheetIds);
    if (!copies.length) return false;
    const lines = copies
      .map((copy) =>
        t("calculationSheets.subprojectDeleteLine", {
          sheet: copy.calculation_sheet_no,
          project: copy.project_name,
        })
      )
      .join("\n");
    return askYesNo(t("calculationSheets.subprojectDeletePrompt", { lines }));
  } catch (err) {
    console.error("Error checking sub-project calculation sheets:", err);
    return false;
  }
}
