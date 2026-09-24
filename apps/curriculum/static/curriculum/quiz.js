/*
 * Quiz engine: instant, reload-free feedback + asynchronous progress saving.
 *
 * This script only flips data-* attributes. All motion (border/background colour,
 * explanation fade + height, metric pulse) is CSS in quiz.html: compositor-friendly
 * properties, <= 250ms, ease-out, disabled by prefers-reduced-motion.
 */
(() => {
  const quiz = document.querySelector("[data-quiz]");
  if (!quiz) return;

  const questions = [...quiz.querySelectorAll("[data-question]")];
  const scoreEl = quiz.querySelector("[data-score]");
  const progressEl = quiz.querySelector("[data-progress]");
  const countEl = quiz.querySelector("[data-mastered-count]");
  const totalEl = quiz.querySelector("[data-mastered-total]");
  const chipEl = quiz.querySelector("[data-mastered-chip]");
  const errorEl = quiz.querySelector("[data-save-error]");
  const total = Number(quiz.dataset.total) || questions.length;

  const PULSE_MS = 200; // matches duration-200 in the template
  let saving = false;

  const setExplanation = (question, open) => {
    const panel = question.querySelector("[data-explanation]");
    // `inert` keeps hidden text out of the tab order and the accessibility tree.
    panel.toggleAttribute("inert", !open);
  };

  const render = () => {
    const answered = questions.filter((q) => q.dataset.answered === "true").length;
    const correct = questions.filter((q) => q.dataset.result === "correct").length;
    scoreEl.textContent = String(correct);
    progressEl.style.transform = `scaleX(${total ? answered / total : 0})`;
    return { answered, correct };
  };

  // --- Metrics micro-interaction --------------------------------------------
  const pulse = () => {
    if (!countEl) return;
    countEl.dataset.pulse = "true";
    window.setTimeout(() => (countEl.dataset.pulse = "false"), PULSE_MS);
  };

  const showMastered = (show) => {
    if (chipEl) chipEl.dataset.show = show ? "true" : "false";
  };

  const setCount = (value) => {
    if (countEl) countEl.textContent = String(value);
  };

  // --- Progress saving --------------------------------------------------------
  const saveCompletion = async () => {
    if (saving || quiz.dataset.completed === "true") return;
    saving = true;
    if (errorEl) errorEl.hidden = true;

    // Optimistic: the UI moves instantly, the server response then reconciles it.
    const before = Number(countEl?.textContent) || 0;
    quiz.dataset.completed = "true";
    setCount(before + 1);
    showMastered(true);
    pulse();

    try {
      const response = await fetch(quiz.dataset.completeUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRFToken": quiz.dataset.csrf, Accept: "application/json" },
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const { stats } = await response.json();
      setCount(stats.mastered);
      if (totalEl) totalEl.textContent = String(stats.total);
    } catch (error) {
      // Roll back so the metric never claims progress that wasn't stored.
      quiz.dataset.completed = "false";
      setCount(before);
      showMastered(false);
      if (errorEl) errorEl.hidden = false;
    } finally {
      saving = false;
    }
  };

  // --- Answering --------------------------------------------------------------
  const answer = (question, chosen) => {
    if (question.dataset.answered === "true") return;
    const isCorrect = chosen.dataset.correct === "true";

    question.querySelectorAll("[data-choice]").forEach((choice) => {
      choice.disabled = true;
      if (choice === chosen) {
        choice.dataset.state = isCorrect ? "correct" : "wrong";
      } else if (choice.dataset.correct === "true") {
        choice.dataset.state = "reveal"; // show the right answer after a miss
      } else {
        choice.dataset.state = "dimmed";
      }
    });

    question.dataset.answered = "true";
    question.dataset.result = isCorrect ? "correct" : "wrong";
    setExplanation(question, true);

    // Quiz completed successfully: last question answered and every answer right.
    const { answered, correct } = render();
    if (answered === total && correct === total) saveCompletion();
  };

  const reset = () => {
    questions.forEach((question) => {
      delete question.dataset.answered;
      delete question.dataset.result;
      question.querySelectorAll("[data-choice]").forEach((choice) => {
        choice.disabled = false;
        choice.dataset.state = "idle";
      });
      setExplanation(question, false);
    });
    render();
  };

  quiz.addEventListener("click", (event) => {
    const choice = event.target.closest("[data-choice]");
    if (choice) return answer(choice.closest("[data-question]"), choice);
    if (event.target.closest("[data-retry]")) reset();
  });

  render();
})();
