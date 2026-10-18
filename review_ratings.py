"""Rating validation and summaries for consented, moderated guest reviews."""
from decimal import Decimal, ROUND_HALF_UP
def rating_value(value, required=False):
    if value in (None, '') and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)) or str(value) not in ('1','2','3','4','5'):
        raise ValueError('Choose a whole-number rating from 1 to 5.')
    return int(value)

def rating_summary(reviews):
    values=[]
    for review in reviews:
        if review.get('status')!='published' or review.get('permission') is not True or review.get('experience_type','guest')!='guest':
            continue
        try:value=rating_value(review.get('rating'))
        except ValueError:continue
        if value is not None:values.append(value)
    average=str((Decimal(sum(values))/len(values)).quantize(Decimal('0.1'),rounding=ROUND_HALF_UP)) if values else None
    return dict(count=len(values),average=average)
