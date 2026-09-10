# email_sender.py
import os
import smtplib
from email.message import EmailMessage


def send_emergency_email(attachment_path="tracking_details.xlsx"):
    try:
        sender_email = "emergencyperson007@gmail.com"
        password = "PUT_APP_PASSWORD_HERE"   # App password (no spaces)
        recipient_email = "Yachekrishnareddy@gmail.com"
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        msg = EmailMessage()
        msg.set_content("""
        EMERGENCY ALERT!

        I'm in an emergency situation and need your help immediately.
        Please check on me as soon as possible.
        
        Note: The recent activity tracking log is attached to this email.
        """)

        msg['Subject'] = '🚨 EMERGENCY ALERT - Need Assistance'
        msg['From'] = sender_email
        msg['To'] = recipient_email

        # Attach the Excel file if it exists in the folder
        if os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as f:
                file_data = f.read()
                file_name = os.path.basename(attachment_path)
            
            # Add the attachment to the email message
            msg.add_attachment(
                file_data, 
                maintype='application', 
                subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                filename=file_name
            )

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)

        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)