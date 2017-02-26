import sys
import datetime
import requests
import re
import lxml.html

# Function to handle known and unknown exceptions


def except_handling(err):
    if type(err) is requests.ConnectionError:
        print('\nNo response from www.flyniki.com')
    elif type(err) in (ValueError, KeyError):
        print('\nWrong data format from www.flyniki.com')
    elif type(err) is str:
        print(err)
    else:
        print('\nPlease send this text to developers:')
        print(err)


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

# Function takes 3 optional arguments. By default function return list
# of all Fly Niki departures airports.
# Use searchfor='destinations' to return list of all Fly Niki
# destinations airports
# Use dep_iata = 'IATA code departure airport' and
# searchfor='destinations' to return list of all available airports
# for flights from departure airport.
# Use silence = False to print result list of airports on the screen


def get_airports_from_site(departures='',
                           searchfor='departures', silence=True):

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
    if not silence:
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


# Function to primary test search query:
# (Not empty, 3-4 parameters, not used special args '-h' or '-iata')
# silence = True to not display error messages on the screen

def check_numbers_of_variables(variables, silence):
    err_msg = ''
    result = True
    if len(variables) == 0 or variables == ['']:
        err_msg = '\nEmpty search,you must enter 3 or 4 parametres'
        result = False
    else:
        if variables[0].lower() in ['h', '-h', 'help', '-help']:
            err_msg = '\nFor the search query to "Fly Niki" enter the search' \
                      ' parameters through the space:\n[departure airport ' \
                      'IATA code] [destination airport IATA code] [departure' \
                      ' date] [return date]\nThe last parameter is not ' \
                      'required for oneway flight search.\nIATA code ' \
                      'contains 3 uppercase letters. Enter -iata to see the ' \
                      'list of available airports codes.\nDates must be at ' \
                      'DD.MM.YY format. Examples of valid query:' \
                      '\nDME LON 17.04.17 06.05.17\nBER ROM 29.08.17'
            result = False
        elif variables[0].lower() in ['-iata', 'iata']:
            get_airports_from_site(silence=False)
            err_msg = 'This is list of IATA codes sorted by a name of ' \
                      'airport city'
            result = False
        else:
            if not (2 < len(variables) < 5):
                err_msg = '\nWrong number of parametres - you have entered ' \
                          '%d, and should be 3 or 4' % len(variables)
                result = False
    if not silence and err_msg != '':
        print(err_msg)
    return result


# Function to check IATA codes at search query:
# (3 uppercase letters, dest_iata do not match dep_iata)
# If check_iata_online = True also checks:
# (Availability dest_iata and dep_iata on flyniki.com,
# availability route dest_iata-dep_iata)
# silence = True to not display error messages ob the screen


def check_iata(dep, dest, silence, check_iata_online):
    dep = dep.upper()
    dest = dest.upper()
    err_msg = ''
    if len(dep) != 3 or re.match("[A-Z]*$", dep) is None:
        err_msg += '\nIncorrect departure airport IATA code format %s. ' \
                   'Use AAA format.' % dep
        dep = False
    elif check_iata_online:
        if dep not in get_airports_from_site():
            err_msg += '\nDeparture airport IATA code %s not found on ' \
                       'flyniki.com' % dep
            dep = False
    if len(dest) != 3 or re.match("[A-Z]*$", dest) is None:
        err_msg += '\nIncorrect destination airport IATA code format ' \
                   '%s. Use AAA format.' % dest
        dest = False
    else:
        if dest == dep:
            err_msg += '\nDestination airport IATA code is the same as ' \
                       'at the departure airport, you do not need a flight'
            dest = False
        else:
            if check_iata_online:
                if dest not in get_airports_from_site(
                        searchfor='destinations'):
                    err_msg += '\nDestinations airport IATA code %s not' \
                               ' found on flyniki.com' % dest
                    dest = False
                else:
                    if dep and dest not in \
                            get_airports_from_site(dep, 'destinations'):
                        err_msg += '\nIncorrect destination airport. Fly' \
                                   ' Niki does not carry out flights on ' \
                                   'a given route %s - %s' % (dep, dest)
                        dest = False
    if not silence and err_msg != '':
        print(err_msg)
    return dep, dest
# Function to check dates at search query:
# (right format, dest_date >= dep_date >=today)
# silence = True to not display error messages on the screen


def check_dates(dep, dest, silence, delta = 360):
    err_msg = ''
    max_date = datetime.date.today() + datetime.timedelta(days=delta)
    try:
        dep_date = format_date(dep, 'to_date')
        if dep_date < datetime.date.today():
            err_msg += '\nIncorrect departure date %s. It must be at least %s' % (dep, format_date(datetime.date.today(), 'to_str'))
            dep = False
        if dep_date > max_date:
            err_msg += '\nIncorrect departure date %s. It must be earlier than %s' % (dep, format_date(max_date, 'to_str'))
            dep = False
    except ValueError:
        err_msg += '\nIncorrect departure date format %s. Use DD.MM.YY' % dep
        dep = False
    if dest != 'oneway':
        try:
            dest_date = format_date(dest, 'to_date')
            if dep and dest_date < dep_date:
                err_msg += '\nReturn date %s earlier the date of departure. It must be at least %s' % (dest, dep)
                dest = False
            if dest_date > max_date:
                err_msg += '\nIncorrect return date %s. It must be earlier than %s' % (dest, format_date(max_date, 'to_str'))
                dest = False
        except ValueError:
            err_msg += '\nIncorrect return date format %s. Use DD.MM.YY' % dest
            dest = False
    if not silence and err_msg != '':
        print(err_msg)
    return dep, dest


# Function return variables for search request at flyniki.com.
# Use optional argument onerun=True to try get variables from the
# command line and exit the program in case of incorrect data, or
# function offer to re-enter it from keyboard input
# Use optional argument silence=True to no display error messages
# on the screen.
# Use optional argument check_iata_online = False to not online
# checking IATA


def get_fly_variables(onerun=False, silence=False, check_iata_online=True):
    variables = sys.argv[1:] if (len(sys.argv) > 1) else []
    while True:
        count_errs = 0
        err_index = 0
        if len(variables) == 3:
            variables.append('oneway')
        if check_numbers_of_variables(variables, silence):
            variables[0], variables[1] = check_iata(
                variables[0], variables[1], silence, check_iata_online)
            variables[2], variables[3] = check_dates(
                variables[2], variables[3], silence)
            if all(variables):
                return variables
            for index, elem in enumerate(variables):
                if not elem:
                    count_errs += 1
                    err_index = index
            if count_errs == 1:
                if raw_input('\nDo you want re-enter this parameter? '
                             'y/n ') not in ['Y', 'y']:
                    return False
                else:
                    variables[err_index] = raw_input('Enter new parameter:')
                continue
        if onerun or raw_input('\nDo you want re-enter your search query? '
                               'y/n ') not in ['Y', 'y']:
            return False
        variables = raw_input('\nEnter the search parameters through the '
                              'space, -h for help, or -iata for lists of '
                              'IATA codes of airports : ').split(' ')


#


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
    search_data = [('_ajax[templates][]', 'main'),
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
                   ('_ajax[requestParams][oneway]', oneway)]
    cookie = {'remember': '0%3B' + lang + '0%3B' + shop}
    search_request = session.post('http://www.flyniki.com/' + lang +
                                  '/booking/flight/vacancy.php',
                                  cookies=cookie, allow_redirects=False)
    search_url = 'http://www.flyniki.com/' + search_request.headers['location']
    return session.post(search_url, data=search_data)


# tax and currency


def get_tax_and_currency():
    price_overview_html = lxml.html.fromstring(search_data['templates']['priceoverview'])
    tax_string = price_overview_html.xpath('''//*[@class='additionals-tsc']/td[2]/text()''')[0]
    tax_string = tax_string.strip().split(' ')
    currency = tax_string[0]
    tax = float(tax_string[1].replace(',', ''))
    return currency, tax


def empty_result():
    if 'flighttable' not in search_data['templates']['main']:
        print ('No connection found for the entered data')
        return True
    return False


def check_combinability():
    if len(search_html.xpath('''//*[@value='COMF']''')) > 0:
        return False
    return True


#flight_data [error, currency, payment chardge, mix classes, outbound rows, return rows, [outbound], [return]]


def data_processing():
    fare_types = []
    flights = []
    flight_tables = 1 if return_date == 'oneway' else 2
    for table in xrange(1, flight_tables+1):
        flights.append([])
        fare_types.append(search_html.xpath('''(//*[@class='faretypes'])[''' + str(table) + ''']//td/div[1]/label/p/text()'''))
        fly_rows = search_html.xpath('''(//*[@class='flighttable'])[''' + str(table) + ''']//*[@class='flightrow']|(//*[@class='flighttable'])[''' + str(table) + ''']//*[@class='flightrow selected']''')
        for index, row in enumerate(fly_rows):
            flights[table-1].append([])
            flights[table-1][index].append(str(row.xpath('''string(td[2]/span/time[1])''')))
            flights[table-1][index].append(str(row.xpath('''string(td[2]/span/time[2])''')))
            flights[table-1][index].append(str(row.xpath('''string(td[2]/span/strong)''')))
            flights[table-1][index].append(str(row.xpath('''string(td[4]/span)''')))
            for td in xrange(5, 5+len(fare_types[table-1])):
                if len(row.xpath('''string(td[''' + str(td) + ''']/span)''')) == 0:
                    price = row.xpath('''string(td[''' + str(td) + ''']/label/div[2]/span)''')
                    low_price = row.xpath('''string(td[''' + str(td) + ''']/label/div[1]/span)''')
                    if len(price) == 0:
                        price = low_price
                    flights[table-1][index].append(str(price))
                else:
                    flights[table-1][index].append('0')
    return fare_types, flights


def get_string_route():
    route = search_html.xpath('''string((//*[@class='vacancy_route'])[1])''')
    route = str(route.encode(sys.getdefaultencoding(), 'replace'))
    route = route.split(',', 1)[0].strip()
    route = route.split(' ')
    dep_string = ''
    dest_string = ''
    for word in route:
        if word != '?':
            dep_string += word
        else:
            dep_string += ' - '
    if return_date != 'oneway':
        dest_string = dep_string.partition(' - ')
        dest_string = dest_string[2] + dest_string[1] + dest_string[0]
    return dep_string, dest_string


def formate_result():
    flights = flyes
    date = [outbound_date, return_date]
    for table in xrange(0, len(flights)):
        for index, row in enumerate(flights[table]):
            flights[table][index][0] = date[table] + ' ' + row[0]
            if len(row[2]) > 0:
                new_date = format_date(date[table], 'to_date') + datetime.timedelta(days=int(row[2]))
                new_date = format_date(new_date, 'to_str')
                flights[table][index][1] = new_date + ' ' + row[1]
            else:
                flights[table][index][1] = date[table] + ' ' + row[1]
            flights[table][index][3] = row[3].strip()
            for elem in xrange(4,len(row)):
                flights[table][index][elem] = float(row[elem].replace(',',''))
            del flights[table][index][2]
    return flights


#


def print_result():
    print('{0:#>72}'.format(''))
    print( '#' + '{0:^14}'.format('Departure time') + '#' + '{0:^14}'.format('Arrival time') + '#' + '{0:^11}'.format('Duration') + '#' \
        + '{0:^10}'.format('RUB') + '#' + '{0:^16}'.format('Fare class') + '#')
    print('{0:#>72}'.format(''))
    for index, row in enumerate(sorted(flyes[0], key = lambda x:x[3])):
        s = '#' + row[0] + ' ' + row[1] + ' ' + row[2]
        for price_index in xrange(3, 3+len(fares[0])):
            if row[price_index] == 0:
                continue
            s =s + '#' + '{0: =10,}'.format(row[price_index]).replace(',',' ') + '#'
            s =s + '{0:^16}'.format(fares[0][price_index-3]) + '#'
            s = '{0: >71}'.format(s)
            print(s)
            s= '#' + '{0: >42}'.format('')
        print('{0:#>72}'.format(''))
    return
try:
    success = get_fly_variables(silence=False)
    if success:
        dep_iata, dest_iata, outbound_date, return_date = success
        search_data = get_search_data(dep_iata, dest_iata, outbound_date, return_date).json()
        if not empty_result():
            search_html = lxml.html.fromstring(search_data['templates']['main'])
            tax,currency = get_tax_and_currency()
            combinability = check_combinability()
            fares,flyes = data_processing()
            print(tax)
            print(currency)
            print(combinability)
            print(fares)
            print (get_string_route())
            flyes = formate_result()
            print_result()

    else:
        print('End of session')
except Exception as err:
    except_handling(err)
    print('End of session')
