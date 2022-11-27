from datetime import date

date = date.today().year


def year(request):
    return {
        'year': date,
    }
