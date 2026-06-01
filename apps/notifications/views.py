from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from .models import Notification
from .serializers import NotificationSerializer


@extend_schema(tags=['Notifications'])
class NotificationListView(generics.ListAPIView):
   serializer_class = NotificationSerializer
   permission_classes = [IsAuthenticated]
   filterset_fields = ['is_read', 'type']

   def get_queryset(self):
      return Notification.objects.filter(user=self.request.user)


@extend_schema(tags=['Notifications'])
class MarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Mark all notifications as read')
    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'message': 'All notifications marked as read.'})
    

@extend_schema(tags=['Notifications'])
class MarkReadView(APIView):
   permission_classes = [IsAuthenticated]

   @extend_schema(summary='Mark a single notification as read')
   def patch(self, request, pk):
      try:
         notif = Notification.objects.get(id=pk, user=request.user)
         notif.is_read = True
         notif.save()
         return Response(NotificationSerializer(notif).data)
      except Notification.DoesNotExist:
         return Response({'error': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(tags=['Notifications'])
class UnreadCountView(APIView):
   permission_classes = [IsAuthenticated]

   @extend_schema(summary='Get unread notification count')
   def get(self, request):
      count = Notification.objects.filter(user=request.user, is_read=False).count()
      return Response({'unread_count': count})