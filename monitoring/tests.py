import unicodedata
from io import BytesIO

from django.test import TestCase
from django.utils import timezone
from pypdf import PdfReader

from monitoring.models import Company, Mention, Source, SourceType
from monitoring.services.reporting import build_ocp_report_data, render_report_pdf, build_report_html


class ReportPdfContentTests(TestCase):
    def setUp(self) -> None:
        self.company = Company.objects.create(name="OCP")
        self.source_type = SourceType.objects.create(name="Web")
        self.source = Source.objects.create(name="Source Démo", type=self.source_type, url="https://example.com")

    def _extract_pdf_text(self, response) -> str:
        reader = PdfReader(BytesIO(response.content))
        return "".join((page.extract_text() or "") for page in reader.pages)

    def _normalize_text(self, text: str) -> str:
        return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()

    def test_pdf_french_article_with_percentages_and_reasons(self):
        structured = {
            "sentiment_label": "negatif",
            "sentiment_scores": {"positif": 10, "neutre": 20, "negatif": 70},
            "sentiment_reasons": [
                "Ton critique envers OCP.",
                "Mention de risques environnementaux.",
                "Absence de contrepoint positif.",
            ],
            "article_summary": "Cet article présente les activités d'OCP dans un contexte tendu.",
            "risk_level": "modéré",
            "recommendations": ["Préparer une réponse officielle."],
        }
        Mention.objects.create(
            company=self.company,
            source=self.source,
            title="Article test",
            content="Extrait français de test sur OCP.",
            original_url="https://example.com/article",
            published_at=timezone.now(),
            sentiment_label="negative",
            sentiment_score=-0.5,
            is_urgent=True,
            raw_metadata={"llm": {"structured": structured}, "excerpt": "Extrait français de test sur OCP."},
        )

        report_data = build_ocp_report_data()
        response = render_report_pdf(report_data)

        text = self._extract_pdf_text(response)
        normalized = self._normalize_text(text)
        self.assertIn("sentiment global", normalized)
        self.assertRegex(normalized, r"10% positif")
        self.assertRegex(normalized, r"20% neutre")
        self.assertRegex(normalized, r"70% negatif")
        self.assertIn("principales raisons de la decision", normalized)
        self.assertIn("ton critique envers ocp", normalized)
        self.assertIn("resume de l'article", normalized)
        self.assertIn("cet article presente les activites d'ocp", normalized)

    def test_pdf_arabic_and_french_excerpt_renders(self):
        arabic_excerpt = "هذا نص عربي يحتوي على كلمة الفضائح مع une phrase en français."
        structured = {
            "sentiment_label": "negatif",
            "sentiment_scores": {"positif": 5, "neutre": 15, "negatif": 80},
            "sentiment_reasons": ["Contenu diffamatoire.", "Termes très négatifs.", "Concerne OCP directement."],
            "article_summary": "Résumé bilingue sans étiquette. Cet article décrit OCP et son contexte en français malgré la source arabe.",
            "risk_level": "élevé",
            "recommendations": ["Surveiller la source."],
        }
        Mention.objects.create(
            company=self.company,
            source=self.source,
            title="Article arabe",
            content=arabic_excerpt,
            original_url="https://example.com/arabic",
            published_at=timezone.now(),
            sentiment_label="negative",
            sentiment_score=-0.8,
            is_urgent=True,
            raw_metadata={"llm": {"structured": structured}, "excerpt": arabic_excerpt},
        )

        report_data = build_ocp_report_data()
        response = render_report_pdf(report_data)
        text = self._extract_pdf_text(response)
        self.assertIn("resume de l'article", self._normalize_text(text))
        self.assertIn("resume bilingue sans etiquette", self._normalize_text(text))

    def test_pdf_handles_missing_fields_with_fallbacks(self):
        structured = {
            "sentiment_label": "neutre",
            # intentionally missing sentiment_scores and sentiment_reasons
            "article_summary": "",
            "risk_level": "",
            "recommendations": [],
        }
        Mention.objects.create(
            company=self.company,
            source=self.source,
            title="Article incomplet",
            content="Contenu sans données LLM complètes.",
            original_url="https://example.com/incomplet",
            published_at=timezone.now(),
            sentiment_label="neutral",
            sentiment_score=0.0,
            is_urgent=False,
            raw_metadata={"llm": {"structured": structured}},
        )

        with self.assertRaises(ValueError):
            build_ocp_report_data()
