"""Custom PointwiseMetric definitions for the eval harness.

Vertex AI Gen AI Evaluation Service (in this SDK version) ships only
`GROUNDEDNESS` and a combined `QUESTION_ANSWERING_QUALITY` as built-in
pointwise metrics. The four RAGAS-style metrics below are implemented as
`PointwiseMetric` instances with hand-written rubric prompts evaluated by
the service-side autorater.

Each PointwiseMetric produces `{metric}/score` and `{metric}/explanation`
columns in the EvalTask result table.
"""

from __future__ import annotations

from vertexai.evaluation import (
    PointwiseMetric,
    PointwiseMetricPromptTemplate,
)


def build_faithfulness() -> PointwiseMetric:
    return PointwiseMetric(
        metric="faithfulness",
        metric_prompt_template=PointwiseMetricPromptTemplate(
            metric_definition="Whether every factual claim in the response is supported by the retrieved context.",
            criteria={
                "grounding": "Is each claim in the response directly supported by something in the context?",
                "no_fabrication": "Does the response avoid introducing facts that are not in the context?",
                "no_contradiction": "Does the response avoid stating anything that contradicts the context?",
            },
            rating_rubric={
                "5": "Every claim in the response is fully supported by the context.",
                "4": "Almost all claims are supported; one or two minor unsupported details.",
                "3": "About half of the claims are supported.",
                "2": "Most claims are unsupported or fabricated.",
                "1": "Response is largely or entirely unsupported by the context.",
            },
            input_variables=["response", "context"],
        ),
    )


def build_answer_relevancy() -> PointwiseMetric:
    return PointwiseMetric(
        metric="answer_relevancy",
        metric_prompt_template=PointwiseMetricPromptTemplate(
            metric_definition="How directly the response addresses the user's question, regardless of factual accuracy.",
            criteria={
                "directness": "Does the response answer what was actually asked rather than a tangentially related question?",
                "completeness": "Does the response address all parts of the question?",
                "focus": "Is the response on-topic without excessive unrelated detail?",
            },
            rating_rubric={
                "5": "Fully addresses every part of the question, on-topic and focused.",
                "4": "Addresses the question well; minor parts under-covered.",
                "3": "Partially addresses the question; misses or sidesteps key aspects.",
                "2": "Mostly off-topic; only weakly related to the question.",
                "1": "Does not address the question at all.",
            },
            input_variables=["prompt"],
        ),
    )


def build_answer_correctness() -> PointwiseMetric:
    return PointwiseMetric(
        metric="answer_correctness",
        metric_prompt_template=PointwiseMetricPromptTemplate(
            metric_definition="Factual correctness of the response when compared to the reference answer.",
            criteria={
                "factual_alignment": "Do the facts in the response match the reference answer?",
                "absence_of_contradiction": "Does the response avoid stating anything that contradicts the reference?",
                "no_hallucination": "Does the response avoid inventing facts that are not in the reference?",
            },
            rating_rubric={
                "5": "Every claim in the response is consistent with the reference.",
                "4": "Almost all claims are correct; minor inaccuracies.",
                "3": "Roughly half correct; some incorrect or unsupported claims.",
                "2": "Mostly incorrect or contradicts the reference.",
                "1": "Entirely incorrect or fabricated.",
            },
            input_variables=["prompt", "reference"],
        ),
    )


def build_context_precision() -> PointwiseMetric:
    return PointwiseMetric(
        metric="context_precision",
        metric_prompt_template=PointwiseMetricPromptTemplate(
            metric_definition="Fraction of retrieved context chunks that are relevant to the question.",
            criteria={
                "relevance": "Are the retrieved chunks topically aligned with the question?",
                "specificity": "Do the chunks address the specific entities, dates, brands, or metrics asked about?",
            },
            rating_rubric={
                "5": "All retrieved chunks are directly relevant.",
                "4": "Most chunks are relevant; one or two are tangential.",
                "3": "Roughly half the chunks are relevant.",
                "2": "Most chunks are irrelevant; one or two are useful.",
                "1": "Almost none of the chunks are relevant.",
            },
            input_variables=["prompt", "context"],
        ),
    )


def build_context_recall() -> PointwiseMetric:
    return PointwiseMetric(
        metric="context_recall",
        metric_prompt_template=PointwiseMetricPromptTemplate(
            metric_definition="Fraction of factual claims in the reference answer that are supported by the retrieved context.",
            criteria={
                "coverage": "Does the retrieved context contain every fact stated in the reference answer?",
                "support": "Could a reader reconstruct the reference answer using only the retrieved context?",
            },
            rating_rubric={
                "5": "Every claim in the reference is supported by the context.",
                "4": "Most claims are supported; minor facts missing.",
                "3": "About half of the reference's claims are supported.",
                "2": "Few claims are supported.",
                "1": "Almost no claims are supported by the retrieved context.",
            },
            input_variables=["reference", "context"],
        ),
    )


def faithfulness_metric() -> PointwiseMetric:
    """Custom faithfulness metric (response grounded in context)."""
    return build_faithfulness()
