from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from .models import BankAccount, Transaction
from decimal import Decimal


class AccountVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = [
            "kyc_submitted",
            "kyc_verified",
            "verification_date",
            "verification_notes",
            "fully_activated",
            "account_status",
        ]
        read_only_fields = ["fully_activated"]

    def validate(self, data: dict) -> dict:
        kyc_verified = data.get("kyc_verified")
        kyc_submitted = data.get("kyc_submitted")
        verification_date = data.get("verification_date")
        verification_notes = data.get("verification_notes")

        if kyc_verified:
            if not verification_date:
                raise serializers.ValidationError(
                    _("Verification date is required when verifying an account.")
                )
            if not verification_notes:
                raise serializers.ValidationError(
                    _("Verification notes are required when verifying an account.")
                )

            if kyc_submitted and not all(
                [kyc_verified, verification_date, verification_notes]
            ):
                raise serializers.ValidationError(
                    _(
                        "All Verification fields (KYC Verified,verification date and notes) must be"
                        " provided when KYC is submitted"
                    )
                )

        return data


class DepositSerializer(serializers.ModelSerializer):
    account_number = serializers.CharField(max_length=20)
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.1")
    )

    class Meta:
        model = BankAccount
        fields = ["account_number", "amount"]

    def validate_account_number(self, value: str) -> str:
        try:
            account = BankAccount.objects.get(account_number=value)
            self.context["account"] = account
        except BankAccount.DoesNotExist:
            raise serializers.ValidationError(_("Invalid account number."))
        return value

    def to_representation(self, instance: BankAccount) -> str:
        representation = super().to_representation(instance)
        representation["amount"] = str(representation["amount"])
        return representation


class CustomerInfoSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name")
    email = serializers.EmailField(source="user.email")
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = BankAccount
        fields = [
            "account_number",
            "full_name",
            "email",
            "photo_url",
            "account_balance",
            "account_type",
            "currency",
        ]

    def get_photo_url(self, obj) -> None:
        if hasattr(obj.user, "profile") and obj.user.profile.photo_url:
            return obj.user.profile.photo_url
        return None


class UUIDField(serializers.Field):
    def to_representation(self, value) -> str:
        return str(value)


class TransactionSerializer(serializers.ModelSerializer):
    id = UUIDField(read_only=True)
    sender_account = serializers.CharField(max_length=20, required=False)
    receiver_account = serializers.CharField(max_length=20, required=False)
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.1")
    )

    class Meta:
        model = Transaction
        fields = [
            "id",
            "amount",
            "description",
            "status",
            "transaction_type",
            "created_at",
            "sender",
            "receiver",
            "sender_account",
            "receiver_account",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def to_representation(self, instance: Transaction) -> str:
        representation = super().to_representation(instance)
        representation["amount"] = str(representation["amount"])
        representation["sender"] = (
            instance.sender.full_name if instance.sender else None
        )
        representation["receiver"] = (
            instance.receiver.full_name if instance.receiver else None
        )
        representation["sender_account"] = (
            instance.sender_account.account_number if instance.sender_account else None
        )
        representation["receiver_account"] = (
            instance.receiver_account.account_number
            if instance.receiver_account
            else None
        )
        return representation

    def validate(self, data):
        transaction_type = data.get("transaction_type")
        sender_account_number = data.get("sender_account")
        receiver_account_number = data.get("receiver_account")
        amount = data.get("amount")

        try:
            if transaction_type == Transaction.TransactionType.WITHDRAWAL:
                account = BankAccount.objects.get(account_number=sender_account_number)
                data["sender_account"] = account
                data["receiver_account"] = None
                if account.account_balance < amount:
                    raise serializers.ValidationError(
                        "Insufficient funds for withdrawal"
                    )
            elif transaction_type == Transaction.TransactionType.DEPOSIT:
                account = BankAccount.objects.get(
                    account_number=receiver_account_number
                )
                data["sender_account"] = None
                data["receiver_account"] = account
            else:
                sender_account = BankAccount.objects.get(
                    account_number=sender_account_number
                )
                receiver_account = BankAccount.objects.get(
                    account_number=receiver_account_number
                )
                data["sender_account"] = sender_account
                data["receiver_account"] = receiver_account

                if sender_account == receiver_account:
                    raise serializers.ValidationError(
                        "Sender and receiver accounts must be different"
                    )
                if sender_account.currency != receiver_account.currency:
                    raise serializers.ValidationError(
                        "Transfers are only allowed between accounts with the same currency"
                    )
                if sender_account.account_balance < amount:
                    raise serializers.ValidationError("Insufficient funds for transfer")
        except BankAccount.DoesNotExist:
            raise serializers.ValidationError("One or both accounts not found")
        return data


class SecurityQuestionSerializer(serializers.Serializer):
    security_answer = serializers.CharField(max_length=30)

    def validate(self, data: dict) -> dict:
        user = self.context["request"].user
        if data["security_answer"] != user.security_answer:
            raise serializers.ValidationError("Incorrect security answer.")
        return data


class OTPVerificationSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6)

    def validate(self, data: dict) -> dict:
        user = self.context["request"].user
        if not user.verify_otp(data["otp"]):
            raise serializers.ValidationError("Invalid or expired OTP.")
        return data


class UsernameVerificationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=12)

    def validate_username(self, value: dict) -> dict:
        user = self.context["request"].user
        if user.username != value:
            raise serializers.ValidationError("Invalid username.")
        return value


class BankAccountSerializer(serializers.ModelSerializer):
    id = UUIDField(read_only=True)
    annual_interest_rate = serializers.DecimalField(max_digits=5, decimal_places=4, read_only=True)

    class Meta:
        model = BankAccount
        fields = [
            "id",
            "account_number",
            "account_balance",
            "currency",
            "account_type",
            "account_status",
            "is_primary",
            "kyc_submitted",
            "kyc_verified",
            "fully_activated",
            "annual_interest_rate",
            "created_at",
        ]
        read_only_fields = fields


class PendingAccountSerializer(serializers.ModelSerializer):
    """Everything an account executive needs to take a KYC decision."""

    id = UUIDField(read_only=True)
    holder_name = serializers.CharField(source="user.full_name", read_only=True)
    holder_email = serializers.EmailField(source="user.email", read_only=True)
    holder_id_no = serializers.IntegerField(source="user.id_no", read_only=True)
    profile_complete = serializers.SerializerMethodField()
    photo_url = serializers.URLField(source="user.profile.photo_url", read_only=True)
    id_photo_url = serializers.URLField(source="user.profile.id_photo_url", read_only=True)
    signature_photo_url = serializers.URLField(source="user.profile.signature_photo_url", read_only=True)

    class Meta:
        model = BankAccount
        fields = [
            "id",
            "account_number",
            "currency",
            "account_type",
            "account_status",
            "kyc_submitted",
            "kyc_verified",
            "fully_activated",
            "verification_notes",
            "created_at",
            "holder_name",
            "holder_email",
            "holder_id_no",
            "profile_complete",
            "photo_url",
            "id_photo_url",
            "signature_photo_url",
        ]
        read_only_fields = fields

    def get_profile_complete(self, obj) -> bool:
        profile = getattr(obj.user, "profile", None)
        return bool(profile and profile.is_complete_with_next_of_kin())
