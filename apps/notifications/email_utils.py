from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone


def send_html_email(subject, template_name, context, recipient_list):
    """
    Send a styled HTML email using a template.
    Falls back to plain text if the template fails.
    """
    # Always inject shared context
    context.setdefault('subject', subject)
    context.setdefault('frontend_url', settings.FRONTEND_URL)
    context.setdefault('date', timezone.now().strftime('%B %d, %Y %I:%M %p UTC'))

    # Plain text fallback
    lines = [f"Hello {context.get('user_name', 'there')},", '']

    for key, value in context.items():
        if key not in ('subject', 'frontend_url', 'date', 'user', 'user_name'):
            lines.append(f"{key.replace('_', ' ').title()}: {value}")

    lines += ["", 'PipsTrust Team', 'support@pipstrust.com']
    text_content = '\n'.join(lines)

    try:
        html_content = render_to_string(f'emails/{template_name}.html', context)
    except Exception:
        html_content = None

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipient_list,
    )
    if html_content:
        msg.attach_alternative(html_content, 'text/html')

    msg.send(fail_silently=True)