import smtplib
from email.message import EmailMessage

sender = "emergencyperson007@gmail.com"
password = "PUT_APP_PASSWORD_HERE"   # Replace with your App Password (16 chars, no spaces)
recipient = "Yachekrishnareddy@gmail.com"

msg = EmailMessage()
msg.set_content("Test message")
msg['Subject'] = 'Test Email'
msg['From'] = sender
msg['To'] = recipient

try:
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        print("Email sent successfully!")
except Exception as e:
    print(f"Error: {e}")