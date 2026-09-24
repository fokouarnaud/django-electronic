/*
 * Quiz engine: instant, reload-free feedback.
 *
 * This script only flips data-* attributes. All motion (border/background colour,
 * explanation fade + height) is CSS in quiz.html: compositor-friendly properties,
 * <= 250ms, ease-out, disabled by prefers-reduced-motion.
 */
(() => {
  const quiz = document.querySelector("[data-quiz]");
  if (!quiz) return;

  const questions = [...quiz.querySelectorAll("[data-question]")];
  const scoreEl = quiz.querySelector("[data-score]");
  const progressEl = quiz.querySelector("[data-progress]");
  const total = Number(quiz.dataset.total) || questions.length;

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
  };

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
    render();
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
