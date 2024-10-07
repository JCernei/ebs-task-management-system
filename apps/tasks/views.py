from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from rest_framework.generics import GenericAPIView, get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response


class TaskListView(GenericAPIView):
    def get(self, request: Request) -> Response:
        return Response("Hello, world.")
