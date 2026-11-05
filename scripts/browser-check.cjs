/* Runs against a seeded local Flask app. Uses installed Edge; no browser download. */
const { chromium } = require("playwright");
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const screenshots = path.join(root, "docs", "screenshots");
fs.mkdirSync(screenshots, { recursive: true });
const baseURL = process.env.TEST_BASE_URL || "http://127.0.0.1:5000";

(async () => {
  const executablePath =
    process.env.BROWSER_PATH ||
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
  const browser = await chromium.launch({ executablePath, headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1040 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("response", (response) => {
    if (response.status() >= 400)
      errors.push(`${response.status()} ${response.url()}`);
  });
  async function goto(route) {
    const response = await page.goto(baseURL + route);
    assert.equal(response.status(), 200, route);
  }
  async function screenshot(name, fullPage = true) {
    await page.screenshot({
      path: path.join(screenshots, `${name}.png`),
      fullPage,
    });
  }
  async function login(role) {
    await context.clearCookies();
    await goto("/auth/login");
    await page.getByLabel("Email address").fill(`${role}@smartrepair.test`);
    await page.getByLabel("Password", { exact: true }).fill("RepairDemo123!");
    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByRole("button", { name: "Sign in to your workspace" }).click(),
    ]);
  }
  try {
    await goto("/");
    await screenshot("landing");
    await login("admin");
    await screenshot("admin-dashboard");
    await goto("/admin/spare_parts");
    await screenshot("admin-crud");
    await goto("/admin/inventory");
    await screenshot("inventory");
    await goto("/repairs?status=In+Progress");
    await page.locator(".table-main").first().click();
    await page.getByRole("heading", { name: "Repair timeline" }).waitFor();
    await screenshot("repair-tracking");
    await page.setViewportSize({ width: 390, height: 844 });
    await goto("/dashboard");
    const width = await page.evaluate(() => ({
      scroll: document.documentElement.scrollWidth,
      view: window.innerWidth,
    }));
    assert(
      width.scroll <= width.view + 1,
      `Mobile page overflow: ${JSON.stringify(width)}`,
    );
    await page.getByRole("button", { name: "Open navigation" }).click();
    assert.equal(
      await page
        .getByRole("button", { name: "Open navigation" })
        .getAttribute("aria-expanded"),
      "true",
    );
    await page.keyboard.press("Escape");
    await screenshot("mobile-dashboard");
    await page.setViewportSize({ width: 1440, height: 1040 });
    await login("tech");
    await screenshot("technician-dashboard");
    await goto("/technician/availability");
    await page.getByRole("heading", { name: "Available slots" }).waitFor();
    await login("customer");
    await screenshot("customer-dashboard");
    await goto("/customer/diagnosis");
    await page.locator('input[name="symptom_ids"][value="3"]').check();
    await page.locator('input[name="symptom_ids"][value="9"]').check();
    await Promise.all([
      page.waitForURL("**/diagnosis?result=1"),
      page.getByRole("button", { name: "Find possible causes" }).click(),
    ]);
    assert(
      (await page.locator(".result-card").count()) > 0,
      "Diagnosis must return matching rules",
    );
    await screenshot("diagnosis-results");
    await page
      .getByRole("link", { name: "Continue to repair request" })
      .click();
    await page
      .getByLabel("Tell us about the issue")
      .fill(
        "Browser QA: battery is draining quickly and the device restarts during normal use.",
      );
    await Promise.all([
      page.waitForURL(/\/customer\/requests\/\d+$/),
      page.getByRole("button", { name: "Submit repair request" }).click(),
    ]);
    await page.getByRole("heading", { name: "Repair overview" }).waitFor();
    await goto("/customer/devices");
    await page.setViewportSize({ width: 390, height: 844 });
    for (const route of [
      "/dashboard",
      "/customer/diagnosis",
      "/customer/devices",
      "/customer/requests/new",
      "/customer/appointments",
      "/repairs",
    ]) {
      await goto(route);
      const width = await page.evaluate(() => ({
        scroll: document.documentElement.scrollWidth,
        view: window.innerWidth,
      }));
      assert(
        width.scroll <= width.view + 1,
        `Mobile overflow at ${route}: ${JSON.stringify(width)}`,
      );
    }
    await goto("/customer/diagnosis");
    await screenshot("mobile-diagnosis");
    await page.setViewportSize({ width: 1600, height: 1100 });
    await page.goto(
      "file:///" +
        path.join(root, "docs", "database-schema.html").replaceAll("\\", "/"),
    );
    await screenshot("database-schema");
    assert.deepEqual(errors, [], "Browser errors");
    console.log(
      "Browser checks passed: role logins, all dashboards, diagnosis + request submission, mobile navigation, responsive screens, no JS/5xx errors.",
    );
    console.log(`Screenshots saved to ${screenshots}`);
  } finally {
    await context.close();
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
