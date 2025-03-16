from rest_framework import serializers
from .models import Problem, ProblemSet

class ProblemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Problem
        fields = ['qid', 'title', 'description', 'solution']

class ProblemSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProblemSet
        fields = ['sid', 'title', 'problems', 'icon']