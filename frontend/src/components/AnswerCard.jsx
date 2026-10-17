function renderInlineMarkdown(text, keyPrefix = "md") {
    const parts = String(text ?? "").split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g);
    return parts.map((part, index) => {
        if (part.startsWith("**") && part.endsWith("**")) {
            return <strong key={`${keyPrefix}-${index}`}>{part.slice(2, -2)}</strong>;
        }
        if (part.startsWith("` ") && part.endsWith(" `")) {
            return <code key={`${keyPrefix}-${index}`}>{part.slice(1, -1)}</code>;
        }
        if (part.startsWith("`") && part.endsWith("`")) {
            return <code key={`${keyPrefix}-${index}`}>{part.slice(1, -1)}</code>;
        }
        if (part.startsWith("*") && part.endsWith("*")) {
            return <em key={`${keyPrefix}-${index}`}>{part.slice(1, -1)}</em>;
        }
        return part;
    });
}

function MarkdownAnswer({ content }) {
    const lines = String(content ?? "").replace(/\r\n/g, "\n").split("\n");
    const blocks = [];
    let listItems = [];
    let listType = null;

    const flushList = () => {
        if (!listItems.length) return;
        const ListTag = listType === "ordered" ? "ol" : "ul";
        blocks.push(
            <ListTag key={`list-${blocks.length}`}>
                {listItems.map((item, index) => (
                    <li key={`item-${index}`}>{renderInlineMarkdown(item, `list-${blocks.length}-${index}`)}</li>
                ))}
            </ListTag>,
        );
        listItems = [];
        listType = null;
    };

    lines.forEach((line, index) => {
        const trimmed = line.trim();
        const ordered = trimmed.match(/^\d+[.)]\s+(.+)$/);
        const unordered = trimmed.match(/^[-*•]\s+(.+)$/);
        if (ordered || unordered) {
            const nextType = ordered ? "ordered" : "unordered";
            if (listType && listType !== nextType) flushList();
            listType = nextType;
            listItems.push((ordered || unordered)[1]);
            return;
        }
        flushList();
        if (!trimmed) return;
        const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
        if (heading) {
            const Tag = `h${heading[1].length + 2}`;
            blocks.push(<Tag key={`heading-${index}`}>{renderInlineMarkdown(heading[2], `heading-${index}`)}</Tag>);
        } else {
            blocks.push(<p key={`paragraph-${index}`}>{renderInlineMarkdown(trimmed, `paragraph-${index}`)}</p>);
        }
    });
    flushList();
    return <div className="markdown-answer">{blocks}</div>;
}

function AnswerCard({ response }) {
    if (!response) return null;

    return (
        <section className="answer-section">
            <div className="section-heading-row">
                <h2>{response.needs_clarification ? "Clarification needed" : "Answer"}</h2>
                {response.success === true && <span className="result-status-pill">Analysis complete</span>}
            </div>
            {response.needs_clarification ? (
                <div className="clarification">
                    <p>{response.clarification_question || response.answer}</p>
                    {response.clarification_options?.length > 0 && (
                        <ul>{response.clarification_options.map((option, index) => <li key={`${option}-${index}`}>{option}</li>)}</ul>
                    )}
                </div>
            ) : (
                <MarkdownAnswer
                    content={response.answer || (
                        response.success === true
                            ? "The analysis completed, but no answer summary was returned."
                            : "No answer was generated because the analysis did not complete successfully. See the analysis error above for details."
                    )}
                />
            )}
        </section>
    );
}

export default AnswerCard;
