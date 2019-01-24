from datetime import datetime, timedelta
import pytz
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.views import View
from auctionApp.currency import Currency
from auctionApp.forms import AddAuctionForm
from auctionApp.models import Auction
from auctionApp.views import Auctions, admin_mail

# auction = Auction


class AddAuction(View):
    global auction

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('home')

        global rate
        Currency.assert_currency(request)
        currency = request.session['currency']
        rate = Currency.get_rate(currency)

        min_datetime = datetime.now() + timedelta(hours=72)
        max_datetime = datetime.now() + timedelta(days=365)
        min_date = min_datetime.strftime('%Y-%m-%dT%H:%M')
        max_date = max_datetime.strftime('%Y-%m-%dT%H:%M')

        if request.POST:
            form = AddAuctionForm(request.POST)
        else:
            form = AddAuctionForm

        return render(request, 'add_auction.html', {'form': form,
                                                    'rate': rate,
                                                    'min_date': min_date,
                                                    'max_date': max_date})

    def post(self, request):
        tf = '%X %d/%m/%y'
        form = AddAuctionForm(request.POST)
        if form.is_valid():
            request.session['unsaved_auction'] = True
            data = form.cleaned_data
            title = data['title']
            description = data['description']
            starting_price = data['starting_price']

            EET = pytz.timezone('UTC')
            time_closing = request.POST['end_datetime']
            parts = time_closing.split('T')
            year = int(parts[0].split('-')[0])
            month = int(parts[0].split('-')[1])
            day = int(parts[0].split('-')[2])
            hours = int(parts[1].split(':')[0])
            minutes = int(parts[1].split(':')[1])
            time_closing = datetime(year=year, month=month, day=day, hour=hours, minute=minutes).replace(tzinfo=EET)
            time_posted = datetime.now().replace(tzinfo=EET)

            global auction
            auction = Auction(seller_id=request.user.id,
                              seller_name=request.user.username,
                              seller_email=request.user.email,
                              title=title,
                              description=description,
                              starting_price=starting_price,
                              current_price=starting_price,
                              time_closing=time_closing,
                              time_posted=time_posted)

            return render(request, 'confirm_auction.html', {'auction': auction,
                                                            'auction_time_closing': time_closing.strftime('%H:%M %d/%m/%y'),
                                                            'auction_time_posted': time_posted.strftime('%H:%M %d/%m/%y'),
                                                            'starting_price': starting_price,
                                                            'seller_name': request.user.username})

        if request.POST['confirmed'] == 'Yes':
            try:
                if request.session['unsaved_auction']:
                    pass
            except:
                request.session.error_message = 'No pending auction or auction has already been added.'
                return Auctions.get(self, request)

            auction.save()

            message_body = 'Your auction with the title "' + auction.title + '" has been created.\n\n' \
                                                                             'The auction will b e open until ' + \
                           auction.time_closing.strftime(tf) + ' or 5 minutes after the last bid.'
            send_mail('Auction created',
                      message_body,
                      admin_mail,
                      [request.user.email],
                      fail_silently=False)

            del request.session['unsaved_auction']

            request.session.info_message = 'Auction added'
            return Auctions.fetch_auction(request, auction.id)
        else:
            return redirect('home')