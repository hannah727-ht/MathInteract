
import { el, formatDate } from "/js/common.js";
import { postText } from "/js/math.js";

export function questionRow(q, topicLabel) {
  return el("li", { class: "q-row" },
    el("div", { class: `q-answers ${q.solved ? "is-solved" : ""} ${q.answer_count ? "" : "is-empty"}` },
      el("strong", {}, String(q.answer_count)),
      el("span", {}, q.solved ? "solved" : q.answer_count === 1 ? "answer" : "answers")
    ),
    el("div", { class: "q-main" },
      el("a", { class: "q-title", href: `/question.html?id=${q.id}` }, postText(q.title, "q-title-text")),
      el("div", { class: "q-meta" },
        el("span", { class: "chip" }, topicLabel),
        el("span", {}, `asked by ${q.user.username} · ${formatDate(q.created_at)}`)
      )
    )
  );
}
