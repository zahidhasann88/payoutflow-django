from rest_framework.routers import SimpleRouter

from .views import CreatorPayoutViewSet, PayoutBatchViewSet, PayoutRuleViewSet

router = SimpleRouter()
router.register("payout-rules", PayoutRuleViewSet, basename="payout-rule")
router.register("payout-batches", PayoutBatchViewSet, basename="payout-batch")
router.register("payouts", CreatorPayoutViewSet, basename="creator-payout")
