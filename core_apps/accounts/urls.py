from django.urls import path
from .views import (
    AccountListAPIView,
    AccountLookupAPIView,
    AccountVerificationView,
    BankStatsAPIView,
    PendingVerificationListAPIView,
    DepositView,
    InitiateWithdrawalView,
    VerifyUsernameAndWithdrawAPIView,
    InitiateTransferView,
    VerifyOTPView,
    VerifySecurityQuestionView,
    TransactionListAPIView,
    TransactionPDFView,
)

urlpatterns = [
    path("", AccountListAPIView.as_view(), name="account_list"),
    path("lookup/", AccountLookupAPIView.as_view(), name="account_lookup"),
    path("pending/", PendingVerificationListAPIView.as_view(), name="pending_verification"),
    path("stats/", BankStatsAPIView.as_view(), name="bank_stats"),
    path(
        "verify/<uuid:pk>/",
        AccountVerificationView.as_view(),
        name="account_verification",
    ),
    path("deposit/", DepositView.as_view(), name="account_deposit"),
    path(
        "initiate-withdrawal/",
        InitiateWithdrawalView.as_view(),
        name="initiate_withdrawal",
    ),
    path(
        "verify-username-and-withdraw/",
        VerifyUsernameAndWithdrawAPIView.as_view(),
        name="verify_username_and_withdraw",
    ),
    path(
        "transfer/initiate/", InitiateTransferView.as_view(), name="initiate_transfer"
    ),
    path(
        "transfer/verify-security-question/",
        VerifySecurityQuestionView.as_view(),
        name="verify_security_question",
    ),
    path("transfer/verify-otp/", VerifyOTPView.as_view(), name="verify_otp"),
    path("transactions/", TransactionListAPIView.as_view(), name="transaction_list"),
    path("transactions/pdf/", TransactionPDFView.as_view(), name="transaction_pdf"),
]
