
from email_service import send_email

def test_email():
    result = send_email(
        "samanthangiela@gmail.com",
        "Cribsy Email Test",
        """
        <h2>Hello from Cribsy!</h2>
        <p>Your email integration is working.</p>
        <p>This is a test email from your Flask backend.</p>
        """
    )

    if result:
        print("Email successfully accepted by SendGrid!")
    else:
        print("Email failed. Check your configuration.")

if __name__ == "__main__":
    test_email()
