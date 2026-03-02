// ==========================
//  Mini Diorthic JS Toolkit
// ==========================

// Verdicts (authentication outcomes)
const VERDICT = Object.freeze({
  ACCEPT: "ACCEPT",
  REJECT: "REJECT",
  SUSPEND: "SUSPEND",
});

// ------------
// Frame model
// ------------
/**
 * createFrame({ name, wellFormed(expr), judge(expr) })
 * - wellFormed: quick sanity check (keeps nonsense out)
 * - judge:     the frame's adjudicator (decides ACCEPT / REJECT / SUSPEND)
 */
function createFrame({ name, wellFormed, judge }) {
  return { name, wellFormed, judge };
}

// ----------------
// Interface model
// ----------------
/**
 * createInterface(F1, F2, mapExpr)
 * - mapExpr: translate an expression from F1 into something F2 can judge
 */
function createInterface(F1, F2, mapExpr) {
  return { from: F1, to: F2, mapExpr };
}

// ------------------
// Composite + Repair
// ------------------
/**
 * transportVerdict(composite, expr)
 * - judge expr in left frame
 * - translate expr and judge in right frame
 * - return the pair of verdicts
 */
function transportVerdict(composite, expr) {
  const { left, right, iface } = composite;

  // Left side
  const vLeft = left.wellFormed(expr)
    ? left.judge(expr)
    : VERDICT.SUSPEND;

  // Right side (translate then judge)
  const translated = iface.mapExpr(expr);
  const vRight = right.wellFormed(translated)
    ? right.judge(translated)
    : VERDICT.SUSPEND;

  return { vLeft, vRight, translated };
}

/**
 * repair(composite, expr)
 * - if verdicts align -> keep it
 * - if they clash -> SUSPEND (flag the interface as the tension point)
 */
function repair(composite, expr) {
  const { vLeft, vRight } = transportVerdict(composite, expr);
  if (vLeft === vRight) return vLeft;
  return VERDICT.SUSPEND;
}

// ================
// Example Frames
// ================

// 1) "Facts" frame: treats statements as true/false via a tiny lookup table.
const dataset = {
  "sky is blue": true,
  "grass is purple": false,
};
const Facts = createFrame({
  name: "Facts",
  wellFormed: (e) => typeof e?.type === "string" && e.type === "stmt",
  judge: (e) => (dataset[e.text] === true ? VERDICT.ACCEPT
                 : dataset[e.text] === false ? VERDICT.REJECT
                 : VERDICT.SUSPEND),
});

// 2) "Aesthetics" frame: judges by a playful rule—strings with even length “resonate”.
const Aesthetics = createFrame({
  name: "Aesthetics",
  wellFormed: (e) => typeof e?.type === "string" && e.type === "art",
  judge: (e) => (e.payload.length % 2 === 0 ? VERDICT.ACCEPT : VERDICT.REJECT),
});

// 3) A tiny self-reference guard to illustrate the Separation Requirement.
// If an expression marks itself selfReferential, any frame returns SUSPEND.
function withSelfRefGuard(frame) {
  return createFrame({
    name: frame.name + "⟂",
    wellFormed: frame.wellFormed,
    judge: (e) => (e.selfRef ? VERDICT.SUSPEND : frame.judge(e)),
  });
}
const FactsSafe = withSelfRefGuard(Facts);
const AestheticsSafe = withSelfRefGuard(Aesthetics);

// =======================
// Interfaces (translation)
// =======================

// Interface 1: Facts → Aesthetics
// Map a factual statement {type:"stmt", text} to an art expr {type:"art", payload}
// (Here we just use the text as the “payload” string.)
const I_Facts_to_Aesthetics = createInterface(
  FactsSafe,
  AestheticsSafe,
  (expr) => ({ type: "art", payload: String(expr.text || "") })
);

// Compose into a composite for side-by-side judging
const Composite_FA = {
  left: FactsSafe,
  right: AestheticsSafe,
  iface: I_Facts_to_Aesthetics,
};

// ===================
// Try it out (demo!)
// ===================

// Helper to log results nicely
function demo(composite, expr, label = "") {
  const { vLeft, vRight, translated } = transportVerdict(composite, expr);
  const overall = repair(composite, expr);
  console.log("—", label || expr.text || expr.payload || "(expr)");
  console.log("  left:", composite.left.name, "→", vLeft);
  console.log("  xlat:", translated);
  console.log(" right:", composite.right.name, "→", vRight);
  console.log("overall repair verdict:", overall, "\n");
}

// 1) Agreement case
demo(Composite_FA, { type: "stmt", text: "grass is purple" }, "Agreement (both REJECT)");

// 2) Disagreement → SUSPEND (facts unknown, but aesthetics accepts/rejects anyway)
demo(Composite_FA, { type: "stmt", text: "octagons sing softly" }, "Disagreement (→ SUSPEND)");

// 3) Self-reference triggers Separation → SUSPEND immediately
demo(Composite_FA, { type: "stmt", text: "this statement is false", selfRef: true }, "Self-reference (→ SUSPEND)");




// ====== Expression-first repair: add rules to a frame ======
// Wrap a frame with a post-judge policy (doesn't alter wellFormed)
function withPostPolicy(frame, policyFn, nameSuffix = "+policy") {
  return createFrame({
    name: frame.name + nameSuffix,
    wellFormed: frame.wellFormed,
    judge: (e) => policyFn(frame.judge(e), e, frame),
  });
}

// Example policy: enforce bivalence (closed-world) → SUSPEND becomes REJECT
function bivalencePolicy(verdict /*, expr, frame */) {
  return verdict === VERDICT.SUSPEND ? VERDICT.REJECT : verdict;
}

// Apply to Facts frame (keeping the self-ref guard from earlier)
const FactsBivalent = withPostPolicy(FactsSafe, bivalencePolicy, "+biv");

// Rebuild composite using the bivalent Facts
const Composite_FA_biv = {
  left: FactsBivalent,
  right: AestheticsSafe,
  iface: I_Facts_to_Aesthetics,
};

function evaluate(composite, expr, policy = "strict") {
  const { left, right, iface } = composite;
  const leftWF = left.wellFormed(expr);
  const vLeft = leftWF ? left.judge(expr) : VERDICT.SUSPEND;
  const translated = iface.mapExpr(expr);
  const rightWF = right.wellFormed(translated);
  const vRight = rightWF ? right.judge(translated) : VERDICT.SUSPEND;

  if (vLeft === vRight)
    return { overall: vLeft, vLeft, vRight, translated,
             reason: "Frames agree." };

  if (policy === "preferLeft" && vLeft !== VERDICT.SUSPEND)
    return { overall: vLeft, vLeft, vRight, translated,
             reason: `Resolved in favor of ${left.name}.` };

  if (policy === "preferRight" && vRight !== VERDICT.SUSPEND)
    return { overall: vRight, vLeft, vRight, translated,
             reason: `Resolved in favor of ${right.name}.` };

  return { overall: VERDICT.SUSPEND, vLeft, vRight, translated,
           reason: "Frames disagree; suspension issued." };
}

// Helper to compare old vs new behavior
function compare(expr, label = "") {
  console.log("⟶", label || expr.text || expr.payload || "(expr)");
  const a = evaluate(Composite_FA, expr);       // original (allows SUSPEND)
  const b = evaluate(Composite_FA_biv, expr);   // bivalence enforced
  console.log("  ORIGINAL :", a.overall, "| L:", a.vLeft, "R:", a.vRight, "|", a.reason);
  console.log("  BIVALENCE:", b.overall, "| L:", b.vLeft, "R:", b.vRight, "|", b.reason, "\n");
}

// Try the previously “unknown” case
compare({ type: "stmt", text: "octagons sing softly" }, "Unknown fact");

compare({ type: "stmt", text: "sky is blue" }, "Known true");

// Try a known true/false to see no change
compare({ type: "stmt", text: "grass is purple" }, "Known false");

// Self-reference still halts (bivalence doesn’t override Separation)
compare({ type: "stmt", text: "this statement is false", selfRef: true }, "Self-ref");
