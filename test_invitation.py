"""
Test script for invitation system
Run this after setting up the database and email configuration
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from datetime import datetime, timedelta

# Add app to path
sys.path.insert(0, '.')

from app.config import settings
from app.models import User, UserRole
from app.utils.auth import hash_password, create_invitation_token
from app.utils.email import send_email, generate_invitation_email


async def test_email_configuration():
    """Test if email configuration is working"""
    print("\n=== Testing Email Configuration ===")

    if not settings.SMTP_PASSWORD:
        print("❌ SMTP_PASSWORD not set in environment variables")
        print("   Please set SMTP_PASSWORD in your .env file")
        return False

    print(f"✓ SMTP Host: {settings.SMTP_HOST}")
    print(f"✓ SMTP Port: {settings.SMTP_PORT}")
    print(f"✓ SMTP User: {settings.SMTP_USER}")
    print(f"✓ From Email: {settings.SMTP_FROM_EMAIL}")
    print(f"✓ From Name: {settings.SMTP_FROM_NAME}")
    print(f"✓ Frontend URL: {settings.FRONTEND_URL}")

    return True


async def test_send_test_email():
    """Send a test email"""
    print("\n=== Sending Test Email ===")

    test_email = input("Enter email address to send test email to: ").strip()
    if not test_email:
        print("❌ No email provided")
        return False

    html_content = """
    <html>
        <body>
            <h1>Test Email from Claim Chaser</h1>
            <p>If you receive this email, your email configuration is working correctly!</p>
            <p>Timestamp: {}</p>
        </body>
    </html>
    """.format(datetime.utcnow().isoformat())

    print(f"Sending test email to {test_email}...")

    result = await send_email(
        to_email=test_email,
        subject="Test Email from Claim Chaser",
        html_content=html_content
    )

    if result:
        print(f"✓ Test email sent successfully to {test_email}")
        print("  Check your inbox (and spam folder)")
        return True
    else:
        print(f"❌ Failed to send test email to {test_email}")
        print("  Check your SMTP credentials and settings")
        return False


async def test_invitation_flow():
    """Test the complete invitation flow"""
    print("\n=== Testing Invitation Flow ===")

    # Create engine
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    # Create session
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session() as session:
        # Check if admin exists
        stmt = select(User).where(User.email == "claimchaser@maximizedrevenue.com")
        result = await session.execute(stmt)
        admin = result.scalars().first()

        if not admin:
            print("❌ Admin user not found. Run 'python init_db.py' first")
            await engine.dispose()
            return False

        print(f"✓ Admin user found: {admin.email}")

        # Create test invitation user
        test_email = f"test+{datetime.utcnow().timestamp()}@example.com"
        invitation_token = create_invitation_token(test_email)
        invitation_expires = datetime.utcnow() + timedelta(hours=48)

        test_user = User(
            email=test_email,
            full_name="Test User",
            role=UserRole.USER,
            invitation_token=invitation_token,
            invitation_expires=invitation_expires,
            password_set=False,
            is_active=False,
            created_by=admin.id
        )

        session.add(test_user)
        await session.commit()
        await session.refresh(test_user)

        print(f"✓ Created test user: {test_user.email}")
        print(f"  User ID: {test_user.id}")
        print(f"  Invitation Token: {invitation_token[:20]}...")
        print(f"  Token Expires: {invitation_expires}")

        # Generate invitation email
        invitation_url = f"{settings.FRONTEND_URL}/set-password?token={invitation_token}"
        print(f"\n✓ Invitation URL: {invitation_url}")

        # Test email generation
        html_content = generate_invitation_email(
            full_name=test_user.full_name,
            invitation_url=invitation_url,
            inviter_name=admin.full_name
        )

        print("✓ Email content generated")
        print(f"  Email length: {len(html_content)} characters")

        # Ask if user wants to send actual email
        send_actual = input("\nDo you want to send an actual invitation email? (y/n): ").strip().lower()

        if send_actual == 'y':
            recipient = input("Enter recipient email address: ").strip()
            if recipient:
                print(f"Sending invitation email to {recipient}...")
                email_sent = await send_email(
                    to_email=recipient,
                    subject=f"You're invited to join {settings.APP_NAME}",
                    html_content=html_content
                )

                if email_sent:
                    print(f"✓ Invitation email sent to {recipient}")
                else:
                    print(f"❌ Failed to send invitation email to {recipient}")

        # Clean up test user
        await session.delete(test_user)
        await session.commit()
        print(f"\n✓ Cleaned up test user")

    await engine.dispose()
    return True


async def test_database_schema():
    """Test if database schema is up to date"""
    print("\n=== Testing Database Schema ===")

    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        try:
            # Try to query users with new fields
            stmt = select(
                User.id,
                User.email,
                User.invitation_token,
                User.invitation_expires,
                User.password_set
            ).limit(1)

            result = await session.execute(stmt)
            result.fetchall()

            print("✓ Database schema is up to date")
            print("  New fields present:")
            print("    - invitation_token")
            print("    - invitation_expires")
            print("    - password_set")

            await engine.dispose()
            return True

        except Exception as e:
            print(f"❌ Database schema is outdated or incomplete")
            print(f"   Error: {str(e)}")
            print("\n   Please run:")
            print("   1. Drop existing database or")
            print("   2. Run: python init_db.py")

            await engine.dispose()
            return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Claim Chaser - Invitation System Test")
    print("=" * 60)

    # Test 1: Email configuration
    config_ok = await test_email_configuration()
    if not config_ok:
        print("\n⚠️  Email configuration incomplete. Some tests will be skipped.")

    # Test 2: Database schema
    schema_ok = await test_database_schema()
    if not schema_ok:
        print("\n❌ Database schema test failed. Cannot continue.")
        return

    # Test 3: Invitation flow
    flow_ok = await test_invitation_flow()

    # Test 4: Send test email (optional)
    if config_ok:
        print("\n" + "=" * 60)
        send_test = input("Do you want to send a test email? (y/n): ").strip().lower()
        if send_test == 'y':
            await test_send_test_email()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"  Email Configuration: {'✓' if config_ok else '❌'}")
    print(f"  Database Schema: {'✓' if schema_ok else '❌'}")
    print(f"  Invitation Flow: {'✓' if flow_ok else '❌'}")
    print("=" * 60)

    if config_ok and schema_ok and flow_ok:
        print("\n✓ All tests passed! Invitation system is ready.")
        print("\nNext steps:")
        print("1. Start the backend: uvicorn app.main:app --reload")
        print("2. Use the API to invite users")
        print("3. Check the API documentation: http://localhost:8000/docs")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
