from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from notification.utils import notif_counts


class NotifBase(APIView):
	authentication_classes = [SessionAuthentication]
	permission_classes = [IsAuthenticated]


class APINotifBadge(NotifBase):
	"""Total badge lonceng + rincian per jenis (dipanggil tiap 5 detik oleh notification.js)."""
	def get(self, request, format=None):
		_, c = notif_counts(request.user)
		return Response({'value': c['total'], 'pendente': c['pendente'], 'rejeitadu': c['rejeitadu']})


class APINotifPendente(NotifBase):
	def get(self, request, format=None):
		_, c = notif_counts(request.user)
		return Response({'value': c['pendente']})


class APINotifRejeitadu(NotifBase):
	def get(self, request, format=None):
		_, c = notif_counts(request.user)
		return Response({'value': c['rejeitadu']})
