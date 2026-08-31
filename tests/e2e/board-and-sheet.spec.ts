import { expect, test } from "@playwright/test";

test("board view loads the table, party, and DM controls", async ({ page }) => {
  await page.goto("/test-campaign/player=dm");

  await expect(page.getByRole("heading", { name: "DnD Board" })).toBeVisible();
  await expect(page.getByText("You are DM")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Party" })).toBeVisible();
  await expect(page.getByText("Marina")).toBeVisible();
  await expect(page.getByRole("button", { name: "Clear Scene" })).toBeVisible();
  await expect(page.locator("canvas")).toBeVisible();
  await expect(page.getByText(/connected .* connected/)).toBeVisible();
});

test("room state updates do not rewrite the browser URL", async ({ page }) => {
  await page.addInitScript(() => {
    const originalReplaceState = window.history.replaceState.bind(window.history);
    let replaceStateCount = 0;
    window.history.replaceState = (...args) => {
      replaceStateCount += 1;
      return originalReplaceState(...args);
    };
    Object.defineProperty(window, "__replaceStateCount", {
      get: () => replaceStateCount
    });
  });

  await page.goto("/test-campaign/player=Marina");
  await expect(page.getByRole("heading", { name: "DnD Board" })).toBeVisible();
  await page.waitForTimeout(1800);

  await expect.poll(async () => page.evaluate(() => (window as Window & { __replaceStateCount?: number }).__replaceStateCount ?? 0)).toBe(0);
  await expect(page).toHaveURL(/\/test-campaign\/player=Marina$/);
});

test("sheet view opens a character and creates roll cards", async ({ page }) => {
  await page.goto("/test-campaign/player=Marina/sheet");

  await expect(page.getByRole("heading", { name: "Character Sheets" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Marina", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Open Marina" }).click();

  await expect(page.getByRole("heading", { name: "Marina" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Saving Throws" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Attacks" })).toBeVisible();

  await page.getByRole("button", { name: "Roll Check" }).first().click();
  await expect(page.locator(".roll-card", { hasText: "Strength Check" }).filter({ hasText: "Strength" })).toBeVisible();

  await page.getByRole("button", { name: "Roll Save" }).first().click();
  await expect
    .poll(async () => page.locator(".roll-card", { hasText: "Strength" }).count())
    .toBeGreaterThanOrEqual(2);

  await page.getByRole("button", { name: "Attack Roll" }).first().click();
  await expect(page.locator(".roll-card", { hasText: "Attack Roll" }).filter({ hasText: "Longsword" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Short Rest" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Long Rest" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Level up Marina" })).toHaveCount(0);
});

test("DM can rest all character sheets from the sheet overview", async ({ page }) => {
  await page.goto("/test-campaign/player=dm/sheet");

  await expect(page.getByRole("button", { name: "Short Rest" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Long Rest" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Level up Marina" })).toBeVisible();
  await page.getByRole("button", { name: "Short Rest" }).click();

  await page.getByRole("button", { name: "Open Marina" }).click();
  await expect(page.getByRole("button", { name: "Level up Marina" })).toBeVisible();
  const progressionSelect = page.locator(".progression-choice").getByRole("combobox").first();
  if ((await progressionSelect.count()) > 0) {
    await progressionSelect.selectOption({ index: 1 });
    const selectedProgressionValue = await progressionSelect.inputValue();
    await page.waitForTimeout(1800);
    await expect(progressionSelect).toHaveValue(selectedProgressionValue);
  }
  await expect(page.getByRole("button", { name: "Short Rest" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Long Rest" })).toHaveCount(0);

  const abilityStepper = page.getByRole("heading", { name: "Abilities" }).locator("..").locator(".stepper").first();
  const initialUses = await abilityStepper.locator("strong").innerText();
  const [currentUses, maxUses] = initialUses.split("/").map((value) => Number(value));
  await abilityStepper.getByRole("button", { name: "-" }).click();
  await expect(abilityStepper.locator("strong")).toHaveText(`${currentUses - 1}/${maxUses}`);

  await page.getByRole("button", { name: "Back to sheets" }).click();
  await page.getByRole("button", { name: "Short Rest" }).click();
  await page.getByRole("button", { name: "Open Marina" }).click();
  await expect(page.getByRole("heading", { name: "Abilities" }).locator("..").locator(".stepper").first().locator("strong")).toHaveText(`${maxUses}/${maxUses}`);
});

test("sheet roll cards distinguish draggable target rolls and can be cleared", async ({ page }) => {
  await page.goto("/test-campaign/player=dm/sheet");
  await page.getByRole("button", { name: "Open Marina" }).click();

  await page.getByRole("button", { name: "Roll Check" }).first().click();
  const checkRoll = page.locator(".roll-card", { hasText: "Strength Check" }).first();
  await expect(checkRoll).toBeVisible();
  await expect(checkRoll).not.toHaveClass(/draggable/);

  await page.getByRole("button", { name: "Attack Roll" }).first().click();
  const attackRoll = page.locator(".roll-card", { hasText: "Attack Roll" }).first();
  await expect(attackRoll).toBeVisible();
  await expect(attackRoll).toHaveClass(/draggable/);

  await page.getByRole("button", { name: "Clear Rolls" }).click();
  await expect(page.locator(".roll-card")).toHaveCount(0);
});

test("self healing rolls stay visible as resolved sheet rolls", async ({ page }) => {
  await page.goto("/test-campaign/player=dm/sheet");
  await page.getByRole("button", { name: "Open Marina" }).click();

  const secondWindRow = page.locator(".resource-row", { hasText: "Second Wind" });
  await secondWindRow.getByRole("button", { name: "Roll" }).click();
  const secondWindRoll = secondWindRow.locator(".roll-card", { hasText: "Second Wind" });
  await expect(secondWindRoll).toBeVisible();
  await expect(secondWindRoll).not.toHaveClass(/draggable/);

  await page.getByRole("button", { name: "Clear Rolls" }).click();
  await expect(page.locator(".roll-card", { hasText: "Second Wind" })).toHaveCount(0);
});

test("sheet view shows Monster Hunter spells and restores long-rest spell uses", async ({ page }) => {
  await page.goto("/spell-test-campaign/player=dm/sheet");

  await page.getByRole("button", { name: "Open Voss" }).click();
  await expect(page.getByRole("heading", { name: "Spells" })).toBeVisible();
  await expect(page.locator(".spell-row", { hasText: "Detect Magic" })).toBeVisible();
  await expect(page.locator(".spell-row", { hasText: "Protection from Evil and Good" })).toBeVisible();
  await expect(page.getByText(/Monster Hunter .* Level 1 .* Wisdom .* Ritual .* Concentration/)).toBeVisible();

  await page.locator(".spell-row", { hasText: "Protection from Evil and Good" }).getByRole("button", { name: "-" }).click();
  await expect(page.locator(".spell-row", { hasText: "Protection from Evil and Good" }).getByText("0/1")).toBeVisible();

  await page.getByRole("button", { name: "Back to sheets" }).click();
  await page.getByRole("button", { name: "Long Rest" }).click();
  await page.getByRole("button", { name: "Open Voss" }).click();
  await expect(page.locator(".spell-row", { hasText: "Protection from Evil and Good" }).getByText("1/1")).toBeVisible();
});
