function AnswerCard({ response }) {
    if (!response) {
        return null;
    }

    return (
        <section className="answer-section">
            <h2>Answer</h2>

            {response.needs_clarification ? (
                <div className="clarification">
                    <p>{response.clarification_question}</p>

                    {response.clarification_options?.length > 0 && (
                        <ul>
                            {response.clarification_options.map(
                                (option, index) => (
                                    <li key={index}>{option}</li>
                                )
                            )}
                        </ul>
                    )}
                </div>
            ) : (
                <div className="answer">
                    {response.answer}
                </div>
            )}
        </section>
    );
}

export default AnswerCard;