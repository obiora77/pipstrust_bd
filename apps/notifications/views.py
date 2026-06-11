from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from .models import Notification
from .serializers import NotificationSerializer
from apps.users.views import api_response


@extend_schema(tags=['Notifications'])
class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_read', 'type']

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return api_response(data=serializer.data)


@extend_schema(tags=['Notifications'])
class MarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Mark all notifications as read')
    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return api_response(message='All notifications marked as read.')


@extend_schema(tags=['Notifications'])
class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Mark a single notification as read')
    def patch(self, request, pk):
        try:
            notif = Notification.objects.get(id=pk, user=request.user)
            notif.is_read = True
            notif.save()
            return api_response(data=NotificationSerializer(notif).data, message='Notification marked as read.')
        except Notification.DoesNotExist:
            return api_response(message='Notification not found.', status_str='error', http_status=404)


@extend_schema(tags=['Notifications'])
class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Get unread notification count')
    def get(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return api_response(data={'unread_count': count})