from django.core.paginator import Paginator

NUMBER_OF_POST = 10


def get_paginator_obj(queryset, request):
    paginator = Paginator(queryset, NUMBER_OF_POST)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
