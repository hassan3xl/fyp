from django.http import HttpResponse
from django.template.loader import get_template
from weasyprint import HTML, CSS

def generate_pdf_from_html(template_src, context, filename="document.pdf"):
    """
    Generates a PDF from an HTML template.
    """
    template = get_template(template_src)
    html_content = template.render(context)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'

    HTML(string=html_content).write_pdf(response, presentational_hints=True)
    return response
