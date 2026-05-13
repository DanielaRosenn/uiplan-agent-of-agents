import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";

const requireFromWeb = createRequire(
  path.join(process.cwd(), "package.json"),
);
const { chromium } = requireFromWeb("@playwright/test");

const width = 1440;
const height = 900;
const url = process.argv[2] || "http://127.0.0.1:5174/";
const repoRoot = path.resolve(process.cwd(), "../..");
const outDir = path.join(repoRoot, "docs", "assets", "uiplan-showcase");
const rawVideoDir = path.join(outDir, "raw");
const webmPath = path.join(outDir, "uiplan-showcase-screen-recording.webm");
const mp4Path = path.join(outDir, "uiplan-showcase-screen-recording.mp4");
const srtPath = path.join(outDir, "uiplan-showcase-screen-recording.srt");
const scriptPath = path.join(outDir, "uiplan-showcase-script.md");

mkdirSync(rawVideoDir, { recursive: true });

const scenes = [
  {
    title: "Project Landing",
    caption:
      "UiPlan Studio turns Cursor work into an end-to-end UiPath planning workspace: business context, solution design, tasks, evidence, and build guidance.",
    action: async (page) => {
      await waitForUi(page);
    },
    seconds: 7,
  },
  {
    title: "Four Project Modes",
    caption:
      "The top bar follows the UiPath delivery lifecycle: Orient, Decide, Execute, and Verify, so every user knows where they are in the planning flow.",
    action: async (page) => {
      await clickByText(page, "ORIENT");
    },
    seconds: 7,
  },
  {
    title: "Header Metrics",
    caption:
      "The header keeps the project actionable: current phase, blocker count, next action, and approval state stay visible while the team works.",
    action: async () => {},
    seconds: 7,
  },
  {
    title: "Plan Overview",
    caption:
      "The overview shows the planning contract: spec.md defines the brief, plan.md defines the UiPath solution, and tasks.md drives delivery.",
    action: async (page) => {
      await clickByText(page, "OVERVIEW");
      await scrollActiveContent(page, 360);
    },
    seconds: 8,
  },
  {
    title: "Cursor and CopilotKit Workflow",
    caption:
      "The workflow is designed for Cursor plus CopilotKit-style collaboration: the plan is readable by people and structured enough for agents to execute.",
    action: async (page) => {
      await clickByText(page, "EXECUTE");
      await clickByText(page, "KANBAN");
    },
    seconds: 8,
  },
  {
    title: "Open the Spec",
    caption:
      "The spec is the business entry point. It captures scope, actors, acceptance, and the AS-IS problem before any UiPath build work begins.",
    action: async (page) => {
      await openExecutePlanWorkspace(page);
      await clickFileNav(page, "spec.md");
      await clickTab(page, "SECTIONS");
      await scrollActiveContent(page, -900);
    },
    seconds: 9,
  },
  {
    title: "Spec Diagrams",
    caption:
      "Spec diagrams make the current process visible. They help business users confirm what happens today and where automation should create value.",
    action: async (page) => {
      await clickTab(page, "DIAGRAMS");
      await scrollActiveContent(page, 420);
    },
    seconds: 9,
  },
  {
    title: "Open the Plan",
    caption:
      "The plan turns that business intent into a UiPath architecture: workflows, runtime sequence, Orchestrator resources, integrations, and handoff gates.",
    action: async (page) => {
      await clickFileNav(page, "plan.md");
      await clickTab(page, "SECTIONS");
      await scrollActiveContent(page, -900);
    },
    seconds: 9,
  },
  {
    title: "Plan Diagrams",
    caption:
      "Plan diagrams are the core project-planning layer. They show how Studio workflows, Orchestrator queues and assets, Integration Service, and HITL pieces connect.",
    action: async (page) => {
      await clickTab(page, "DIAGRAMS");
      await scrollActiveContent(page, 450);
    },
    seconds: 9,
  },
  {
    title: "More Plan Diagrams",
    caption:
      "Scrolling through plan.md diagrams shows the delivery story from architecture to execution order, dependencies, evidence, and deployment readiness.",
    action: async (page) => {
      await scrollActiveContent(page, 720);
    },
    seconds: 9,
  },
  {
    title: "Open the Tasks",
    caption:
      "tasks.md is where the plan becomes work. Each task stays tied to the project phase, source plan file, status, and suggested UiPath skill.",
    action: async (page) => {
      await clickFileNav(page, "tasks.md");
      await clickTab(page, "SECTIONS");
      await scrollActiveContent(page, -900);
    },
    seconds: 9,
  },
  {
    title: "Task Board",
    caption:
      "The task board gives builders an execution view: what is done, what is active, what is open, and which UiPath capability should be used next.",
    action: async (page) => {
      await clickTab(page, "KANBAN");
      await scrollActiveContent(page, 420);
    },
    seconds: 9,
  },
  {
    title: "AS-IS Process",
    caption:
      "AS-IS shows the current manual process by actor and handoff, so business users can validate what happens today before automation starts.",
    action: async (page) => {
      await clickByText(page, "ORIENT");
      await clickByText(page, "AS-IS");
      await scrollActiveContent(page, -900);
    },
    seconds: 8,
  },
  {
    title: "Progressive Disclosure",
    caption:
      "Clicking actors or nodes moves from L0 system view into lane, work item, and raw metadata detail without overwhelming the landing view.",
    action: async (page) => {
      await clickFirstCanvasLikeElement(page);
    },
    seconds: 8,
  },
  {
    title: "TO-BE UiPath Target",
    caption:
      "TO-BE translates the future process into concrete UiPath building blocks: workflows, integrations, queues, assets, and Action Center points.",
    action: async (page) => {
      await clickByText(page, "TO BE");
    },
    seconds: 8,
  },
  {
    title: "AS-IS to TO-BE Narrative",
    caption:
      "Compare mode explains the transformation: manual handoffs become orchestrated UiPath components with owners, evidence, and readiness criteria.",
    action: async (page) => {
      await clickByText(page, "COMPARE");
    },
    seconds: 8,
  },
  {
    title: "Execute Mode",
    caption:
      "Execute mode is the builder workspace. It brings together tasks, docs, diagram context, and the next build action inside Cursor.",
    action: async (page) => {
      await clickByText(page, "EXECUTE");
      await clickByText(page, "KANBAN");
      await clickFileNav(page, "tasks.md");
      await scrollActiveContent(page, -500);
    },
    seconds: 8,
  },
  {
    title: "Skills and Integrations Hub",
    caption:
      "The Skills and Integrations Hub maps work to the right UiPath skills, Orchestrator queues and assets, Integration Service connections, and Action Center touchpoints.",
    action: async (page) => {
      await ensureTextVisible(page, "SKILLS & INTEGRATIONS HUB");
    },
    seconds: 8,
  },
  {
    title: "Decide Mode",
    caption:
      "Decide mode focuses review conversations on risks, assumptions, open decisions, and owners before the team commits to build work.",
    action: async (page) => {
      await clickByText(page, "DECIDE");
    },
    seconds: 7,
  },
  {
    title: "Verify Mode",
    caption:
      "Verify mode supports handoff readiness by tying the business story, architecture, task completion, and evidence into one traceable view.",
    action: async (page) => {
      await clickByText(page, "VERIFY");
    },
    seconds: 7,
  },
  {
    title: "How to Use It",
    caption:
      "End to end: start in Orient with business users, refine the spec and plan in Cursor, execute tasks with the right UiPath skills, then Verify for handoff.",
    action: async (page) => {
      await clickByText(page, "RESET CLEAN VIEW");
    },
    seconds: 8,
  },
];

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width, height },
  recordVideo: { dir: rawVideoDir, size: { width, height } },
});

const page = await context.newPage();
await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
await installSubtitleOverlay(page);

const timeline = [];
let elapsed = 0;
for (const scene of scenes) {
  await scene.action(page);
  await setCaption(page, scene.caption);
  timeline.push({
    title: scene.title,
    caption: scene.caption,
    start: elapsed,
    end: elapsed + scene.seconds,
  });
  await page.waitForTimeout(scene.seconds * 1000);
  elapsed += scene.seconds;
}

await setCaption(page, "");
const video = page.video();
await context.close();
await browser.close();

const recordedPath = await video.path();
copyFileSync(recordedPath, webmPath);
writeFileSync(srtPath, buildSrt(timeline), "utf8");
writeFileSync(scriptPath, buildScript(timeline, url), "utf8");

let finalVideoPath = webmPath;
if (hasExecutable("ffmpeg")) {
  execFileSync("ffmpeg", [
    "-y",
    "-i",
    webmPath,
    "-c:v",
    "libx264",
    "-pix_fmt",
    "yuv420p",
    "-movflags",
    "+faststart",
    mp4Path,
  ], { stdio: "inherit" });
  if (existsSync(mp4Path)) {
    finalVideoPath = mp4Path;
  }
}

console.log(JSON.stringify({
  video: finalVideoPath,
  webm: webmPath,
  subtitles: srtPath,
  script: scriptPath,
}, null, 2));

async function waitForUi(page) {
  await page.waitForSelector("text=UIPLAN WORKFLOW BUILDER", { timeout: 60000 });
  await page.waitForTimeout(1500);
}

async function installSubtitleOverlay(page) {
  await page.addStyleTag({
    content: `
      #uiplan-video-subtitles {
        position: fixed;
        left: 50%;
        bottom: 28px;
        transform: translateX(-50%);
        max-width: 1120px;
        width: calc(100vw - 96px);
        z-index: 2147483647;
        background: rgba(15, 23, 42, 0.88);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 14px;
        box-shadow: 0 20px 60px rgba(15, 23, 42, 0.35);
        padding: 16px 22px;
        font-family: Inter, Segoe UI, Arial, sans-serif;
        font-size: 24px;
        line-height: 1.35;
        font-weight: 650;
        text-align: center;
        pointer-events: none;
      }
    `,
  });
  await page.evaluate(() => {
    const existing = document.getElementById("uiplan-video-subtitles");
    if (existing) existing.remove();
    const subtitle = document.createElement("div");
    subtitle.id = "uiplan-video-subtitles";
    subtitle.setAttribute("aria-hidden", "true");
    document.body.appendChild(subtitle);
  });
}

async function setCaption(page, text) {
  await page.evaluate((caption) => {
    const subtitle = document.getElementById("uiplan-video-subtitles");
    if (subtitle) subtitle.textContent = caption;
  }, text);
}

async function clickByText(page, text) {
  const normalized = text.toLowerCase().replace(/\s+/g, " ").trim();
  const clicked = await page.evaluate((target) => {
    const isVisible = (element) => {
      const rect = element.getBoundingClientRect();
      const style = window.getComputedStyle(element);
      return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
    };
    const elements = Array.from(document.querySelectorAll("button, [role='button'], a, div, span"));
    const exact = elements.find((element) =>
      isVisible(element) &&
      (element.textContent || "").toLowerCase().replace(/\s+/g, " ").trim() === target
    );
    const fuzzy = elements.find((element) =>
      isVisible(element) &&
      (element.textContent || "").toLowerCase().replace(/\s+/g, " ").includes(target)
    );
    const match = exact || fuzzy;
    if (!match) return false;
    match.scrollIntoView({ block: "center", inline: "center" });
    match.click();
    return true;
  }, normalized);
  if (!clicked) {
    console.warn(`Could not find clickable text: ${text}`);
  }
  await page.waitForTimeout(900);
}

async function openExecutePlanWorkspace(page) {
  await clickByText(page, "EXECUTE");
  await clickByText(page, "KANBAN");
}

async function clickFileNav(page, label) {
  const clicked = await page.evaluate((targetLabel) => {
    const planFilesHeader = Array.from(document.querySelectorAll("*")).find((element) =>
      (element.textContent || "").trim() === "PLAN FILES"
    );
    const panel = planFilesHeader?.parentElement;
    const buttons = Array.from((panel || document).querySelectorAll("button"));
    const match = buttons.find((button) =>
      (button.textContent || "").toLowerCase().includes(targetLabel.toLowerCase())
    );
    if (!match) return false;
    match.scrollIntoView({ block: "center", inline: "nearest" });
    match.click();
    return true;
  }, label);
  if (!clicked) {
    console.warn(`Could not find plan file: ${label}`);
  }
  await page.waitForTimeout(1000);
}

async function clickTab(page, labelPrefix) {
  const clicked = await page.evaluate((targetPrefix) => {
    const target = targetPrefix.toLowerCase();
    const buttons = Array.from(document.querySelectorAll("button"));
    const match = buttons.find((button) =>
      (button.textContent || "").trim().toLowerCase().startsWith(target)
    );
    if (!match) return false;
    match.scrollIntoView({ block: "center", inline: "center" });
    match.click();
    return true;
  }, labelPrefix);
  if (!clicked) {
    console.warn(`Could not find tab: ${labelPrefix}`);
  }
  await page.waitForTimeout(900);
}

async function scrollActiveContent(page, deltaY) {
  await page.evaluate((amount) => {
    const candidates = Array.from(document.querySelectorAll("div"))
      .filter((element) => {
        const style = window.getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return (
          rect.width > 420 &&
          rect.height > 260 &&
          rect.top > 90 &&
          (style.overflowY === "auto" || style.overflow === "auto") &&
          element.scrollHeight > element.clientHeight
        );
      })
      .sort((a, b) => b.getBoundingClientRect().width - a.getBoundingClientRect().width);
    const target = candidates[0] || document.scrollingElement || document.documentElement;
    target.scrollBy({ top: amount, behavior: "smooth" });
  }, deltaY);
  await page.waitForTimeout(1200);
}

async function clickFirstCanvasLikeElement(page) {
  await page.evaluate(() => {
    const candidates = Array.from(document.querySelectorAll("button, [role='button'], svg g, svg rect"));
    const target = candidates.find((element) => {
      const rect = element.getBoundingClientRect();
      return rect.width > 24 && rect.height > 16 && rect.top > 120 && rect.left > 40;
    });
    if (target) {
      target.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
    }
  });
  await page.waitForTimeout(900);
}

async function ensureTextVisible(page, text) {
  await page.evaluate((targetText) => {
    const match = Array.from(document.querySelectorAll("*")).find((element) =>
      (element.textContent || "").includes(targetText)
    );
    if (match) match.scrollIntoView({ block: "center", inline: "nearest" });
  }, text);
  await page.waitForTimeout(900);
}

function buildSrt(items) {
  return items.map((item, index) => [
    String(index + 1),
    `${formatSrtTime(item.start)} --> ${formatSrtTime(item.end)}`,
    item.caption,
    "",
  ].join("\n")).join("\n");
}

function buildScript(items, sourceUrl) {
  const rows = items.map((item, index) =>
    `## ${index + 1}. ${item.title}\n\n**Time:** ${formatClock(item.start)}-${formatClock(item.end)}\n\n${item.caption}\n`
  ).join("\n");
  return `# UiPlan Showcase Screen Recording Script\n\nSource URL: ${sourceUrl}\nResolution: ${width}x${height}\n\n${rows}`;
}

function formatSrtTime(seconds) {
  const totalMs = Math.round(seconds * 1000);
  const ms = totalMs % 1000;
  const totalSeconds = Math.floor(totalMs / 1000);
  const s = totalSeconds % 60;
  const totalMinutes = Math.floor(totalSeconds / 60);
  const m = totalMinutes % 60;
  const h = Math.floor(totalMinutes / 60);
  return `${pad(h)}:${pad(m)}:${pad(s)},${String(ms).padStart(3, "0")}`;
}

function formatClock(seconds) {
  const totalSeconds = Math.round(seconds);
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${pad(m)}:${pad(s)}`;
}

function pad(value) {
  return String(value).padStart(2, "0");
}

function hasExecutable(command) {
  try {
    const lookup = process.platform === "win32" ? "where.exe" : "which";
    execFileSync(lookup, [command], { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}
