from django.core.management.base import BaseCommand

from custom.models import Municipality

MUNICIPIOS = [
    ('AL', 'Aileu'), ('AN', 'Ainaro'), ('BC', 'Baucau'), ('BB', 'Bobonaro'), ('CL', 'Cova Lima'),
    ('DL', 'Dili'), ('ER', 'Ermera'), ('LT', 'Lautem'), ('LQ', 'Liquiçá'), ('MT', 'Manatuto'),
    ('MF', 'Manufahi'), ('OE', 'Oecusse'), ('VQ', 'Viqueque'),
]


class Command(BaseCommand):
    help = 'Hatama munisípiu 13 Timor-Leste (idempotente). Postu/Suku/Aldeia hatama liu husi admin.'

    def handle(self, *args, **opts):
        n = 0
        for code, name in MUNICIPIOS:
            _, created = Municipality.objects.get_or_create(code=code, defaults={'name': name})
            n += created
        self.stdout.write(self.style.SUCCESS(f'{n} munisípiu foun; total {Municipality.objects.count()}.'))
