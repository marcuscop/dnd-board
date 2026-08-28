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
});

test("DM can rest all character sheets from the sheet overview", async ({ page }) => {
  await page.goto("/test-campaign/player=dm/sheet");

  await expect(page.getByRole("button", { name: "Short Rest" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Long Rest" })).toBeVisible();

  await page.getByRole("button", { name: "Open Marina" }).click();
  await expect(page.getByRole("button", { name: "Short Rest" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Long Rest" })).toHaveCount(0);

  await page.getByRole("heading", { name: "Abilities" }).locator("..").getByRole("button", { name: "-" }).first().click();
  await expect.poll(async () => page.getByText("2/3").count()).toBeGreaterThanOrEqual(1);

  await page.getByRole("button", { name: "Back to sheets" }).click();
  await page.getByRole("button", { name: "Short Rest" }).click();
  await page.getByRole("button", { name: "Open Marina" }).click();
  await expect.poll(async () => page.getByText("3/3").count()).toBeGreaterThanOrEqual(1);
});
