import sys
import datetime
import requests
import re
import lxml.html


class ParametersError(RuntimeError):
    pass


class SearchError(RuntimeError):
    pass


"""
Functions for checking search parameters
"""

# Function return parameters for search request at flyniki.com.
# Use optional argument check_iata_online = False to not online
# checking IATA


def check_search_parameters(search_parameters, check_iata_online=True):
    while True:
        count_errs = 0
        err_index = 0
        if len(search_parameters) == 3:
            search_parameters.append('oneway')
        check_numbers_of_parameters(search_parameters)
        search_parameters[0], search_parameters[1] = check_iata(
            search_parameters[0].upper(), search_parameters[1].upper(),
            check_iata_online)
        search_parameters[2], search_parameters[3] = check_dates(
            search_parameters[2], search_parameters[3])
        if all(search_parameters):
            return search_parameters
        for index, elem in enumerate(search_parameters):
            if not elem:
                count_errs += 1
                err_index = index
        if count_errs == 1:
            if raw_input('\nDo you want re-enter this parameter? y/n ') \
                    not in ['Y', 'y']:
                sys.exit('\nEnd of session')
            else:
                search_parameters[err_index] = \
                    raw_input('Enter new parameter:')
            continue
        raise ParametersError('\nToo much mistakes in search request')


# Function to primary test search query:
# (Not empty, 3-4 parameters, not used special args '-h' or '-iata')


def check_numbers_of_parameters(search_parameters):
    parameters = len(search_parameters)
    if parameters == 0 or search_parameters == ['']:
        raise ParametersError('\nEmpty search, '
                              'you must enter 3 or 4 parameters')
    keyword = search_parameters[0].lower()
    if keyword in ['h', '-h', 'help', '-help']:
        raise ParametersError('\nFor the search query to "Fly Niki" enter the '
                              'search parameters through the space:\n'
                              '[departure airport IATA code] [destination '
                              'airport IATA code] [departure date] [return '
                              'date]\nThe last parameter is not required for '
                              'oneway flight search.\nIATA code contains 3 '
                              'uppercase letters. Enter -iata to see the list'
                              ' of available airports codes.\nDates must be '
                              'at DD.MM.YY format.Examples of valid query:'
                              '\nDME LON 17.04.17 06.05.17\nBER ROM 29.08.17')
    if keyword in ['-iata', 'iata']:
        get_airports_from_site(show=True)
        raise ParametersError('This is list of IATA codes sorted by a name of '
                              'airport city')
    if parameters not in (3, 4):
        raise ParametersError('\nWrong number of parametres - you have entered'
                              ' %d, and should be 3 or 4' % parameters)


# Function to check IATA codes at search query:
# (3 uppercase letters, dest_iata do not match dep_iata)
# If check_iata_online = True also checks:
# Availability dest_iata and dep_iata on flyniki.com,
# availability route dest_iata-dep_iata


def check_iata(dep_iata, dest_iata, check_iata_online):
    if len(dep_iata) != 3 or re.match("[A-Z]*$", dep_iata) is None:
        print('\nIncorrect departure airport IATA code format '
              '%s. Use AAA format.' % dep_iata)
        dep_iata = False
    else:
        if check_iata_online:
            if dep_iata not in get_airports_from_site():
                print('\nDeparture airport IATA code '
                      '%s not found on flyniki.com' % dep_iata)
                dep_iata = False
    if len(dest_iata) != 3 or re.match("[A-Z]*$", dest_iata) is None:
        print('\nIncorrect destination airport IATA code format '
              '%s. Use AAA format.' % dest_iata)
        dest_iata = False
    else:
        if dest_iata == dep_iata:
            print('\nDestination airport IATA code is the same as at the'
                  ' departure airport, you do not need a flight')
            dest_iata = False
        else:
            if check_iata_online:
                if dest_iata not in get_airports_from_site(
                        searchfor='destinations'):
                    print('\nDestinations airport IATA code '
                          '%s not found on flyniki.com' % dest_iata)
                    dest_iata = False
                else:
                    if dep_iata and dest_iata not in \
                            get_airports_from_site(dep_iata, 'destinations'):
                        print('\nIncorrect destination airport. Fly Niki '
                              'does not carry out flights on a given route '
                              '%s - %s' % (dep_iata, dest_iata))
                        dest_iata = False
    return dep_iata, dest_iata


# Function to check dates at search query:
# correct format, max_date >= dest_date >= dep_date >=today)
# max_date = today + delta


def check_dates(outbound_date, return_date, delta=360):
    max_date = datetime.date.today() + datetime.timedelta(days=delta)
    try:
        dep_date = format_date(outbound_date, 'to_date')
        if dep_date < datetime.date.today():
            print('\nIncorrect departure date %s. It must be at least %s' % (
                outbound_date, format_date(datetime.date.today(), 'to_str')))
            outbound_date = False
        if dep_date > max_date:
            print('\nIncorrect departure date %s. It must be earlier than '
                  '%s' % (outbound_date, format_date(max_date, 'to_str')))
            outbound_date = False
    except ValueError:
        print('\nIncorrect departure date format %s. Use DD.MM.YY'
              % outbound_date)
        outbound_date = False
    if return_date != 'oneway':
        try:
            ret_date = format_date(return_date, 'to_date')
            if outbound_date and \
               ret_date < format_date(outbound_date, 'to_date'):
                print('\nReturn date %s earlier the date of departure. '
                      'It must be at least %s' % (return_date, outbound_date))
                return_date = False
            if ret_date > max_date:
                print('\nIncorrect return date %s. It must be earlier than '
                      '%s' % (return_date, format_date(max_date, 'to_str')))
                return_date = False
        except ValueError:
            print('\nIncorrect return date format %s. Use DD.MM.YY'
                  % return_date)
            return_date = False
    return outbound_date, return_date


# Formating date


def format_date(date, to_type):
    if to_type == 'to_date':
        date = datetime.datetime.strptime(date, '%d.%m.%y')
        return datetime.datetime.date(date)
    if to_type == 'to_str':
        return datetime.date.strftime(date, '%d.%m.%y')
    if to_type == 'to_flyniki':
        date = datetime.datetime.strptime(date, '%d.%m.%y')
        date = datetime.datetime.date(date)
        return datetime.date.strftime(date, '%Y-%m-%d')
    if to_type == 'to_datetime':
        return datetime.datetime.strptime(date, '%d.%m.%y %H:%M')


# Function takes 3 optional arguments. By default function return list
# of all Fly Niki departures airports.
# Use searchfor='destinations' to return list of all Fly Niki
# destinations airports
# Use dep_iata = 'IATA code departure airport' and
# searchfor='destinations' to return list of all available airports
# for flights from departure airport.
# Use show = True to print result list of airports on the screen


def get_airports_from_site(departures='', searchfor='departures', show=False):
    airport_request_params = {'searchfor': searchfor,
                              'searchflightid': '0',
                              'departures[]': departures,
                              'destinations[]': '',
                              'suggestsource[0]': 'activeairports',
                              'withcountries': '0',
                              'withoutroutings': '0',
                              'promotion[id]': '',
                              'promotion[type]': '',
                              'get_full_suggest_list': 'true',
                              'routesource[0]': 'airberlin',
                              'routesource[1]': 'partner'}
    airports = {}
    airport_request = requests.get('http://www.flyniki.com/en/site/'
                                   'json/suggestAirport.php',
                                   params=airport_request_params)
    for airport in tuple(airport_request.json()['suggestList']):
        airports[airport['code']] = airport['name']
    if not airports:
        raise TypeError('Failed to obtain list of airports')
    if show:
        help_iata = ''
        for index, elem in enumerate(sorted(airports.items(),
                                            key=lambda (k, v): v)):
            iata = elem[0].encode(sys.getdefaultencoding(), 'replace')
            city = elem[1].encode(sys.getdefaultencoding(), 'replace')
            if index % 3 == 0:
                help_iata += '\n%s - %s' % \
                             (iata, '{0: <25.25}'.format(city[:20]))
            else:
                help_iata += '%s - %s' % \
                             (iata, '{0: <25.25}'.format(city[:20]))
        print(help_iata)
    return airports


"""
Functions to get data from site and checking for errors
"""


def get_search_data(dep_iata_, dest_iata_, outbound_date_, return_date_,
                    lang='en', shop='RU'):
    session = requests.Session()
    outbound_date_ = format_date(outbound_date_, 'to_flyniki')
    if return_date_ == 'oneway':
        return_date_ = ''
        oneway = 'on'
    else:
        return_date_ = format_date(return_date_, 'to_flyniki')
        oneway = ''
    request_data = [('_ajax[templates][]', 'main'),
                    ('_ajax[templates][]', 'priceoverview'),
                    ('_ajax[templates][]', 'infos'),
                    ('_ajax[templates][]', 'flightinfo'),
                    ('_ajax[requestParams][departure]', dep_iata_),
                    ('_ajax[requestParams][destination]', dest_iata_),
                    ('_ajax[requestParams][returnDeparture]', ''),
                    ('_ajax[requestParams][returnDestination]', ''),
                    ('_ajax[requestParams][outboundDate]', outbound_date_),
                    ('_ajax[requestParams][returnDate]', return_date_),
                    ('_ajax[requestParams][adultCount]', '1'),
                    ('_ajax[requestParams][childCount]', '0'),
                    ('_ajax[requestParams][infantCount]', '0'),
                    ('_ajax[requestParams][openDateOverview]', ''),
                    ('_ajax[requestParams][oneway]', oneway),
                    ('_ajax[templates][])', 'dateoverview')]
    cookie = {'remember': '0%3B' + lang + '0%3B' + shop}
    search_request = session.post('http://www.flyniki.com/' + lang +
                                  '/booking/flight/vacancy.php',
                                  cookies=cookie, allow_redirects=False)
    search_url = 'http://www.flyniki.com/' + search_request.headers['location']
    return session.post(search_url, data=request_data)


# Function to checking data for errors and result availability


def check_for_result_errors(search_data):
    if 'error' in search_data:
        err_msg = lxml.html.fromstring(search_data['error']).\
            xpath('''string(//*[@class = 'wrapper'])''')
        raise SearchError('\n' +
                          err_msg.encode(sys.getdefaultencoding(), 'replace'))
    if 'No connections' in search_data['templates']['dateoverview']:
        raise SearchError('\nNo connections found for the entered data. '
                          'However, connections are available on days either '
                          'side. Keep searching!')


"""
Functions for getting search result
"""


# The gathering of information on flights from the received data.
# flights_ = [outbound table, return table]. Each table list of:
# [departure time, arrival time, difference in days, duration,
# [price1, price2,...]]. Price is selected from two possible
# (current and lowest), defaults to the current, but sometimes
# it does not exist. If price 'notbookable' - price = 0
# fare_types = [[outbound fare types][return fare types]]. Each table
# list of used cabin classes.


def data_processing(search_html, return_date):
    fare_types = []
    flights_ = []
    flight_tables = 1 if return_date == 'oneway' else 2
    for table in xrange(1, flight_tables+1):
        flights_.append([])
        fare_types.append(search_html.xpath('''(//*[@class='faretypes'])['''
                                            + str(table) + ''']
                                            //td/div[1]/label/p/text()'''))
        fly_rows = search_html.xpath('''(//*[@class='flighttable'])
                                    [''' + str(table) + ''']
                                    //*[@class='flightrow']|
                                    (//*[@class='flighttable'])
                                    [''' + str(table) + ''']
                                    //*[@class='flightrow selected']''')
        for index, row in enumerate(fly_rows):
            flights_[table-1].append([])
            flights_[table-1][index].append(str(row.xpath('''string(td[2]
                                                        /span/time[1])''')))
            flights_[table-1][index].append(str(row.xpath('''string(td[2]
                                                        /span/time[2])''')))
            flights_[table-1][index].append(str(row.xpath('''string(td[2]
                                                        /span/strong)''')))
            flights_[table-1][index].append(str(row.xpath('''string(td[4]
                                                        /span)''')))
            for td in xrange(5, 5+len(fare_types[table-1])):
                if len(row.xpath('''string(td[''' + str(td) + ''']
                                    /span)''')) == 0:
                    price = row.xpath('''string(td[''' + str(td) + ''']
                                        /label/div[2]/span)''')

                    low_price = row.xpath('''string(td[''' + str(td) + ''']
                                        /label/div[1]/span)''')
                    if len(price) == 0:
                        price = low_price
                    flights_[table-1][index].append(str(price))
                else:
                    flights_[table-1][index].append('0')
    return fare_types, flights_


# Adds the date to the time
# (and difference in days to arrival date)
# Converts all prices to float
# Deleting the difference in days
# return flights = [[[departure datetime, arrival datetime,
#                  duration, [price1, price2,...]],...][...]]


def format_result(flights, outbound_date, return_date):
    date = [outbound_date, return_date]
    for table in xrange(0, len(flights)):
        for index, row in enumerate(flights[table]):
            flights[table][index][0] = date[table] + ' ' + row[0]
            if len(row[2]) > 0:
                new_date = format_date(date[table], 'to_date') + \
                           datetime.timedelta(days=int(row[2]))
                new_date = format_date(new_date, 'to_str')
                flights[table][index][1] = new_date + ' ' + row[1]
            else:
                flights[table][index][1] = date[table] + ' ' + row[1]
            flights[table][index][3] = row[3].strip()
            for elem in xrange(4, len(row)):
                flights[table][index][elem] = float(row[elem].replace(',', ''))
            del flights[table][index][2]
    return flights


# Get route string.
# dep. citi(iata) - dest. city(iata) if oneway, else:
# dep. citi(iata) - dest. city(iata) - dep. citi(iata)


def get_string_route(search_html, return_date):
    route = search_html.xpath('''string((//*[@class='vacancy_route'])[1])''')
    route = str(route.encode(sys.getdefaultencoding(), 'replace'))
    route = route.split(',', 1)[0].strip()
    route = route.split(' ')
    route_string = ''
    for word in route:
        if word != '?':
            route_string += word
        else:
            route_string += ' - '
    if return_date != 'oneway':
        route_string = route_string + ' - ' + route_string.split(' - ')[0]
    return route_string.upper()


def get_currency_and_tax(search_data):
    price_overview_html = lxml.html.fromstring(search_data
                                               ['templates']['priceoverview'])
    tax_string = price_overview_html.xpath('''//*[@class='additionals-tsc']
                                            /td[2]/text()''')[0]
    tax_string = tax_string.strip().split(' ')
    currency = tax_string[0].encode(sys.getdefaultencoding(), 'replace')
    currency = '(' + currency + ')'
    tax = float(tax_string[1].replace(',', ''))
    return currency, tax


"""
Functions for printing results
"""


# Function to check the possibility of cobmining different cabin class.
# The only way that i have found


def check_combinability(search_html):
    if len(search_html.xpath('''//*[@value='COMF']''')) > 0:
        return False
    return True


# Print oneway result sorted by a time of departure


def print_oneway_result(flights, fares, currency, tax, route):
    print('\n' + route + '\n')
    print('{0: ^20}{1: ^20}{2: ^15}{3: ^12}{4: ^20}{5: ^25}'.format(
        'Departure time', 'Arrival time', 'Duration', '  Price' + currency,
        'Cabin class', 'Total price with tax' + currency)+'\n')
    for row in sorted(flights[0], key=lambda x: x[0]):
        s = '{0: ^20}{1: ^20}{2: ^15}'.format(row[0], row[1], row[2])
        for price_index in xrange(3, 3+len(fares[0])):
            if row[price_index] == 0:
                continue
            s = s + '{0: >12,.2f}'.format(row[price_index]).\
                replace(',', ' ') + '  {0: ^18}'\
                .format(fares[0][price_index-3]) + '{0: >15,.2f}'\
                .format(row[price_index]+tax).replace(',', ' ')
            s = '{0: >87}'.format(s)
            print(s)
            s = '{0: >55}'.format('')
        print('{0:-^112}'.format(''))


# Print mix result sorted by a total amount.
# First, we create a list of possible options.
# Check the following parametres:
# 1)Arrival datetime of outbound at least an 1 hour >
# than the departure datetime of return.
# 2)outbound price !=0 (notbookable price)
# 3)return price !=0
# 4)we can mix the cabin classes or they are the same
# if all ok we append result to mix_flights - list of:
# [outbound departure datetime, outbound arrival datetime,
# outbound duration, outbound price, outbound cabin class,
# return departure datetime, return arrival datetime,
# return duration, return price, return cabin class,
# total price, total price with tax]


def print_mix_result(flights, fares, currency, tax, route, mix_fare):
    print('\n' + route + '\n')
    mix_flights = []
    for out_row in flights[0]:
        for ret_row in flights[1]:
            if (format_date(out_row[1], 'to_datetime') +
                    datetime.timedelta(hours=1)) > \
                    format_date(ret_row[0], 'to_datetime'):
                continue
            for out_price_index in xrange(3, 3+len(fares[0])):
                out_price = out_row[out_price_index]
                for ret_price_index in xrange(3, 3+len(fares[1])):
                    ret_price = ret_row[ret_price_index]
                    if (out_price == 0) or (ret_price == 0):
                        continue
                    out_fare = fares[0][out_price_index-3]
                    ret_fare = fares[1][ret_price_index-3]
                    if (not mix_fare) and (out_fare != ret_fare):
                        continue
                    total_price = out_price + ret_price
                    full_price = total_price + tax
                    mix_flights.append([out_row[0], out_row[1], out_row[2],
                                        out_price, out_fare,
                                        ret_row[0], ret_row[1], ret_row[2],
                                        ret_price, ret_fare,
                                        total_price, full_price])
    if len(mix_flights) == 0:
        raise SearchError('\nNo connections found for the entered data.')
    print('%s flight options\n' % len(mix_flights))
    print('{0: ^15}{1: ^20}{2: ^20}{3: ^15}{4: ^12}{5: ^20}{6: ^20}'
          '{7: ^25}'.format('Direction', 'Departure time', 'Arrival time',
                            'Duration', '  Price' + currency,
                            'Cabin class', 'Total price' + currency,
                            'Total price with tax' + currency) + '\n')
    for elem in sorted(mix_flights, key=lambda x: x[11]):
        print('{0: ^15}{1: ^20}{2: ^20}{3: ^15}'.format
              ('outbound', elem[0], elem[1], elem[2])
              + '{0: >12,.2f}'.format(elem[3]).replace(',', ' ')
              + '{0: ^20}'.format(elem[4]))
        print('{0: >100}'.format('') + '{0: >15,.2f}'.
              format(elem[10]).replace(',', ' ')
              + '{0: >20,.2f}'.format(elem[11]).replace(',', ' '))
        print('{0: ^15}{1: ^20}{2: ^20}{3: ^15}'.format
              ('return', elem[5], elem[6], elem[7]) +
              '{0: >12,.2f}'.format(elem[8]).replace(',', ' ') +
              '{0: ^20}'.format(elem[9]))
        print('{0:-^142}'.format(''))


# Main function.


def flyniki_search(search_parameters):
    search_parameters = search_parameters[1:] if (len(search_parameters) > 1)\
        else []
    while True:
        try:
            dep_iata, dest_iata, outbound_date, return_date = \
                check_search_parameters(search_parameters)
            search_data = get_search_data(dep_iata, dest_iata, outbound_date,
                                          return_date).json()
            check_for_result_errors(search_data)
            search_html = lxml.html.fromstring(search_data
                                               ['templates']['main'])
            fares, flights = data_processing(search_html, return_date)
            flights = format_result(flights, outbound_date, return_date)
            currency, tax = get_currency_and_tax(search_data)
            if return_date == 'oneway':
                print_oneway_result(flights, fares, currency, tax,
                                    get_string_route(search_html, return_date))
            else:
                print_mix_result(flights, fares, currency, tax,
                                 get_string_route(search_html, return_date),
                                 check_combinability(search_html))
        except (ParametersError, SearchError) as err:
            print(err)
        except requests.ConnectionError:
            print('\nNo response from www.flyniki.com')
        except (ValueError, KeyError, IndexError):
            print('\nWrong data format from www.flyniki.com')
        if raw_input('\nDo you want re-enter your search query? y/n ') \
                not in ['Y', 'y']:
            sys.exit('\nEnd of session')
        search_parameters = raw_input('\nEnter the search parameters through '
                                      'the space, -h for help, or -iata for '
                                      'lists of IATA codes of '
                                      'airports : ').split(' ')
        continue


if __name__ == "__main__":
    flyniki_search(sys.argv)
