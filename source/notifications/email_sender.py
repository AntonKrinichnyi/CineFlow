import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import aiosmtplib
from jinja2 import Enviroment, FileSystemLoader

from source.security.exceptions import BaseEmailError
from source.notifications.interfaces import EmailSenderInterface


class EmailSender(EmailSenderInterface):
    
    def __init__(
        self,
        hostname: str,
        port: int,
        email: str,
        password: str,
        use_tls: bool,
        template_dir: str,
        activation_email_template_name: str,
        activation_complete_email_template_name: str,
        password_email_tempate_name: str,
        password_complete_email_template_name: str,
    ):
        self._hostaname = hostname
        self._port = port
        self._email = email
        self._password = password
        self._use_tls = use_tls
        self._activation_email_template_name = activation_email_template_name
        self._activation_complete_email_template_name = activation_complete_email_template_name
        self._password_email_template_name = password_email_tempate_name
        self._password_complete_email_template_name = password_complete_email_template_name
        
        self._env = Enviroment(loader=FileSystemLoader(template_dir))
    
    async def _send_email(self, recipient: str, subject: str, html_content: str) -> None:
        message = MIMEMultipart
        message["From"] = self._email
        message["To"] = recipient
        message["Subject"] = subject
        message.attach(MIMEText(html_content, "html"))
        
        try:
            smtp = aiosmtplib.SMTP(hostname=self._hostaname, port=self._port, start_tls=self._use_tls)
            await smtp.connect()
            if self._use_tls:
                await smtp.starttls()
            await smtp.login(self._email, self._password)
            await smtp.sendmail(self._email, [recipient], message.as_string())
            await smtp.quit()
        except aiosmtplib.SMTPException as error:
            logging.error(f"Failed to send email to {recipient}: {error}")
            raise BaseEmailError(f"Failed to send email to {recipient}: {error}")
    
    async def send_activation_email(self, email: str, activation_link: str) -> None:
        template = self._env.get_template(self._activation_email_template_name)
        html_content = template.render(email=email, activation_link=activation_link)
        subject = "Account activation"
        await self._send_email(email, subject, html_content)
    
    async def send_activation_complete_email(self, email: str, login_link: str) -> None:
        template = self._env.get_template(self._activation_complete_email_template_name)
        html_content = template.render(email=email, login_link=login_link)
        subject = "Account activated successfully"
        await self._send_email(email, subject, html_content)
    
    async def send_password_reset_email(self, email: str, reset_link: str) -> None:
        template = self._env.get_template(self._password_email_template_name)
        html_content = template.render(email=email, reset_link=reset_link)
        subject = "Password reset request"
        await self._send_email(email, subject, html_content)
    
    async def send_remove_movie(self, email: str, movie_name: str, cart_id: int) -> None:
        html_content = f"""
            <p>Movie "{movie_name}" removed from cart with ID: {cart_id}</p>
        """
        subject = f"{movie_name} removed from cart with id: {cart_id}"
        await self._send_email(email, subject, html_content)
        