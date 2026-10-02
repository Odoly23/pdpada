from django.db.models import Count, F, Q

from config import roles as R
from config.scope import get_role, membru_queryset
from membro.models import Membru


def _group_expr(role):
    """Pa'a data tuir nivel user: nasional→munisípiu, postu→suku, suku→aldeia, aldeia→estadu."""
    if role == R.POSTU:
        return 'aldeia__village__name', 'Suku'
    if role == R.SUKU:
        return 'aldeia__name', 'Aldeia'
    if role == R.ALDEIA:
        return 'estadu', 'Estadu'
    return 'aldeia__village__administrativepost__municipality__name', 'Munisípiu'


def summary(user):
    qs = membru_queryset(user)
    expr, label = _group_expr(get_role(user))
    rows = list(
        qs.values(nome=F(expr)).annotate(
            mane=Count('id', filter=Q(sexu='M')), feto=Count('id', filter=Q(sexu='F')), total=Count('id'),
        ).order_by('nome'))
    if label == 'Estadu':
        names = dict(Membru.Estadu.choices)
        for r in rows:
            r['nome'] = names.get(r['nome'], r['nome'])
    estadu = {e: qs.filter(estadu=e).count() for e in Membru.Estadu.values}
    return {
        'group_label': label, 'rows': rows, 'estadu': estadu,
        'total': sum(r['total'] for r in rows),
        'mane': sum(r['mane'] for r in rows), 'feto': sum(r['feto'] for r in rows),
    }
