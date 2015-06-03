# encoding:utf_8

# Create your views here.
import cStringIO as StringIO
from collections import defaultdict
import os
import json
from cgi import escape
import time
import datetime
from datetime import timedelta
import pprint
from django.contrib.auth import authenticate, login

import math
import operator
from django.core.mail import EmailMessage
from django.core.serializers.json import DjangoJSONEncoder
import itertools
import xhtml2pdf.pisa as pisa

from django.contrib import auth
from django.contrib.auth.decorators import login_required, user_passes_test

from django.template.loader import get_template
from django.utils.dateformat import DateFormat

import xlwt
from django.db import connections, DatabaseError
from aplicacion.forms import DatosEntradaScriptForm, formLogin, formTotalVentaPublicidad, formVentaNetaAnual, \
    formPromociones, formVentasCaptura
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext, Context
from aplicacion.models import GruposLoguin
from reportesNorte import settings

from dateutil import relativedelta as rdelta
from datetime import datetime
import reportesNorte
from reportesNorte.settings import STATIC_URL, MEDIA_URL, MEDIA_ROOT, IMAGEN_EXCEL, AUTH_LDAP_USER_SEARCH, \
    AUTH_LDAP_GROUP_SEARCH


def inicio(request):
    if request.user.is_authenticated():
        inicializarVariables(request)
        return render_to_response('menuPrincipal.html', context_instance=RequestContext(request))
    else:
        return loginView(request)


@login_required
def menuReportesEstadisticos(request):
    request.session['titulo'] = 0  # Esto es para que el "volver" de ventas mensuales permita cargar de nuevo el FORM

    return render_to_response('reportesEstadisticos/menuReportesEstadisticos.html',
                              context_instance=RequestContext(request))


def inicializarVariables(request):
    request.session[
        'puedeGuardarMes'] = False  # es ponemos para poder visualizar el grid de totales publicidad sin necesidad de acceder a  algun form
    request.session['fechaDesde'] = 0
    request.session['fechaHasta'] = 0
    request.session['codigoRemoto'] = 0
    request.session['titulo'] = 0
    request.session['lista_resultados'] = 0
    request.session['agrupacion'] = 0
    request.session['lista_totales'] = 0
    request.session['lista_ccA'] = 0
    request.session['keys'] = 0
    request.session['data'] = 0
    request.session['headers'] = 0
    request.session['listaCCA_Grupo'] = 0
    request.session['mesDesdeAGuardar'] = 0
    request.session['anioDesdeAGuardar'] = 0
    request.session['idLineaPublicidad'] = 0
    request.session['mensaje'] = 0
    request.session['dia'] = 0  # variable de session para asegurarnos de que se guarde un mes completo
    request.session['diccionarioRecyDesc'] = 0
    request.session['lista_grafico_recydesc'] = 0
    request.session['listaBrutaParaGrafico'] = 0
    request.session['listaParaGraficoJson'] = 0
    request.session['listaParaGrafico'] = 0
    request.session['listaParaGraficoPorFormaDePago'] = 0
    # variable que almacena la longitud de una lista para representar los totales en el excel.
    request.session['reporteConTotales'] = 0
    request.session['listaCaptura'] = 0
    request.session['listaPromociones'] = 0
    request.session['listaPromocionesGrupo'] = 0
    request.session['listaVendedorHoraSegunFormaDePago'] = 0
    request.session['listaVendedorHora'] = 0
    request.session['listaBrutaParaVendedores'] = 0
    request.session['detalleRecargosyDescuentos'] = 0


def transformacionGenerica(data):
    resultado = []
    if data['cms_puro'] == None:  # Esto se hace en casos donde no se trajo cms_puro sino que centimetros.
        data['cms_puro'] = data['centimetros']

    if data['RecargoColor'] == None:
        data['RecargoColor'] = 0

    if data['RecargoLogo'] == None:
        data['RecargoLogo'] = 0

    valorAnuncio = data['ValorAnuncio']
    if data['SupSaCh'] == 109:
        valorAnuncio = data['ValorAnuncio'] - data['RecargoColor']

    descManual = 0
    if data['DescuentoAMano'] < 0:
        descManual = ((valorAnuncio + data['RecargoColor'] + data['RecargoLogo']) -
                      (data['DescPromocion'] + data['DescConvenio'] + data['DescAgencia'])) * data[
            'DescuentoAMano'] * (-1) / 100

    totalRecargo = data['RecargoColor'] + data['RecargoLogo'] + descManual

    totalBruto = valorAnuncio + totalRecargo

    descCms = 0  # Preguntar!! lo hacemos ahora porque está tirando un error. Pero por formula de excel no tenía el if de totalBruto
    if totalBruto != 0:
        descCms = math.ceil((round(data['DescPromocion'] / totalBruto, 2) * data['cms_puro']))

    cmsNeto = data['cms_puro'] - descCms

    descAMano = 0
    if data['DescuentoAMano'] > 0:
        descAMano = ((((valorAnuncio + data['RecargoColor'] + data['RecargoLogo'] + descManual) -
                       (data['DescPromocion'] + data['DescConvenio'] + data['DescAgencia'])) *
                      data['DescuentoAMano']) / 100)

    totalDescuento = data['DescPromocion'] + data['DescConvenio'] + data['DescAgencia'] + descAMano

    netoSinIva = totalBruto - totalDescuento

    resultado = {'valorAnuncio': valorAnuncio, 'descManual': descManual, 'totalRecargo': totalRecargo,
                 'totalBruto': totalBruto, 'totalDescuento': totalDescuento, 'descCms': descCms, 'cmsNeto': cmsNeto,
                 'descAMano': descAMano, 'netoSinIva': netoSinIva}
    return resultado


@login_required
def reportesFormasDePago(request):
    try:
        if request.method == 'POST':
            formulario = DatosEntradaScriptForm(request.POST)
            if formulario.is_valid():

                cursor = connections['sqlserver2008'].cursor()
                fechaDesde = formulario.cleaned_data['fechaDesde']
                df = DateFormat(fechaDesde)
                fechaDesde = df.format('Y-d-m')

                fechaDesdeModoLatino = df.format('d/m/Y')

                fechaHasta = formulario.cleaned_data['fechaHasta']
                df = DateFormat(fechaHasta)
                fechaHasta = df.format('Y-d-m')
                fechaHastaModoLatino = df.format('d/m/Y')

                request.session['fechaDesde'] = fechaDesdeModoLatino
                request.session['fechaHasta'] = fechaHastaModoLatino

                formaDePago = formulario.cleaned_data['formaDePago']
                formaDePagoMas = formulario.cleaned_data['formaDePagoMas']
                codRemoto = formulario.cleaned_data['codRemoto']

                if codRemoto == u'1':
                    request.session['codigoRemoto'] = 'Chaco'
                else:
                    request.session['codigoRemoto'] = 'Corrientes'

                cortesias = 885
                compensacion = 885
                reposicion = 885
                otros = ''
                request.session['titulo'] = ''

                # creo variables con strings de nombres de las otras formas de pago, para que se muestre en el template
                otrasFormasDePago = ''
                if formaDePago == u'3':
                    # Variables para mandar con forma de pago = 3
                    for i, data in enumerate(formaDePagoMas):

                        if data == u'6':
                            compensacion = 6
                            request.session['titulo'] = request.session['titulo'] + 'Compensacion'
                        if data == u'7':
                            cortesias = 7
                            if request.session['titulo'] != '' and request.session['titulo'] != 0:
                                request.session['titulo'] = request.session['titulo'] + ' - Cortesias'
                            else:
                                request.session['titulo'] = 'Cortesias'

                        if data == u'8':
                            reposicion = 8
                            if request.session['titulo'] != '' and request.session['titulo'] != 0:
                                request.session['titulo'] = request.session['titulo'] + ' - Reposicion'
                            else:
                                request.session['titulo'] = 'Reposicion'

                        if data == u'5':  # Las otras formas de pago
                            otros = '2 3 9 10 11'
                            otrasFormasDePago = 'Mensual-Tarjeta-Migracion-Cuenta_Interna-Compensacion_Efectivo'
                            if request.session['titulo'] != '' and request.session['titulo'] != 0:
                                # -Mensual-Tarjeta-Migracion-Cuenta_Interna-Compensacion_Efectivo
                                request.session['titulo'] = request.session['titulo'] + ' - Otras Formas de Pago'
                            else:
                                request.session['titulo'] = 'Otras Formas de Pago'

                cursor.execute("SELECT * FROM AvisosFormasDePagoCOMPLETO(%s, %s, %s, %s, %s, %s, %s, %s)",
                               (fechaDesde, fechaHasta, formaDePago, codRemoto, cortesias, compensacion, reposicion,
                                otros))

                listaAux = dictfetchall(cursor)

                request.session['lista_resultados'] = listaAux

                if formaDePago == u'1':
                    request.session['agrupacion'] = 'Grupo'
                else:
                    request.session['agrupacion'] = 'Aviso'

                lista = []

                for data in (listaAux):
                    resultado = transformacionGenerica(data)
                    grupo = data['Grupo']
                    if grupo == None:
                        grupo = 99  # Grupo 99 es contado y grupo 0 tambien lo agregamos como contado
                    else:
                        grupo = int(data['Grupo'])
                        if grupo == 10:
                            grupo = 9  # Esto es porque Directas es 9 y 10.
                        if grupo == 0:
                            grupo = 99  # Grupo 99 es contado y grupo 0 tambien lo agregamos como contado

                    dictionary = dict(Grupo=grupo, AgenciaCliente=data['AgenciaCliente'], Codigo=data['Codigo'],
                                      Aviso=data['Aviso'], TotalCms=data['cms_puro'], DescCms=resultado['descCms'],
                                      CmsNeto=resultado['cmsNeto'],
                                      ValorAnuncio=resultado['valorAnuncio'], RecargoColor=data['RecargoColor'],
                                      RecargoLogo=data['RecargoLogo'], fechafactura=data['fechafactura'],
                                      nrofactura=data['nrofactura'], nropedido=data['nropedido'],
                                      CodigoAviso=data['CodigoAviso'], OrdenPublicidad=data['OrdenPublicidad'],
                                      DescManual=resultado['descManual'], TotalRecargo=resultado['totalRecargo'],
                                      TotalBruto=resultado['totalBruto'],
                                      DescPromocion=data['DescPromocion'], DescConvenio=data['DescConvenio'],
                                      ComAgencia=data['DescAgencia'],
                                      DescAgencia=resultado['descAMano'], TotalDescuento=resultado['totalDescuento'],
                                      NetoSinIva=resultado['netoSinIva'],
                                      CondIva=data[
                                          'CondImpuesto'])  # esta es la transformación de la lista anterior mediante formulas.
                    lista.append(dictionary)

                request.session['lista_ccA'] = lista

                if formaDePago == u'1':
                    request.session['titulo'] = 'Cuenta Corriente'
                    return render_to_response('reportesEstadisticos/reportesFormasPago/listaCtaCteA.html',
                                              {'agrupacion': 'CuentaCorriente'},
                                              context_instance=RequestContext(request))
                elif formaDePago == u'2':
                    agrupacion = request.session['agrupacion']
                    request.session['titulo'] = 'Contado'
                    fechaDesde = request.session['fechaDesde']
                    fechaHasta = request.session['fechaHasta']
                    codigoRemoto = request.session['codigoRemoto']
                    return render_to_response('reportesEstadisticos/reportesFormasPago/cuentaCorrienteA.html',
                                              {'agrupacion': agrupacion, 'tit': request.session['titulo'],
                                               'fechaDesde': fechaDesde, 'fechaHasta': fechaHasta,
                                               'codigoRemoto': codigoRemoto},
                                              context_instance=RequestContext(request))
                else:
                    titulo = request.session['titulo']
                    agrupacion = request.session['agrupacion']
                    fechaDesde = request.session['fechaDesde']
                    fechaHasta = request.session['fechaHasta']
                    codigoRemoto = request.session['codigoRemoto']
                    return render_to_response('reportesEstadisticos/reportesFormasPago/cuentaCorrienteA.html',
                                              {'agrupacion': agrupacion, 'tit': titulo,
                                               'fechaDesde': fechaDesde,
                                               'fechaHasta': fechaHasta,
                                               'codigoRemoto': codigoRemoto},
                                              context_instance=RequestContext(request))
        else:
            formulario = DatosEntradaScriptForm()

        return render_to_response('reportesEstadisticos/reportesFormasPago/formReportesFormasDePago.html',
                                  {'formulario': formulario},
                                  context_instance=RequestContext(request))
    except Exception as e:

        return HttpResponseRedirect('/errorGeneral', {'mensaje': e.message,
                                                      'tipo': type(e)})  # , context_instance=RequestContext(request)


def someError(request):
    return render_to_response('errorGeneral.html', context_instance=RequestContext(request))


def grupo_check(user, gr=[]):
    # print(GruposLoguin.objects.all())
    var = GruposLoguin.objects.all()
    if hasattr(user, 'ldap_user'):

        try:
            nombreGrupo = user.ldap_user.attrs['memberof'][0]
        except:
            nombreGrupo = user.ldap_user.attrs['distinguishedname'][0]

        # usuarioldap = user.ldap_user
        # if hasattr(usuarioldap,"attrs"):
        #     nombreGrupo = user.ldap_user.attrs['memberof'][0]
        # else:
        #     nombreGrupo = user.ldap_user.dn

        nombreGrupo = nombreGrupo.replace(' ', '')
    else:
        return True

    # for property, value in vars(user.ldap_user).iteritems():
    #     print property, ": ", value

    for grupo in var:

        grupoAux = grupo.nombre.replace(' ', '')
        if grupoAux in nombreGrupo:
            gr.append(grupo.nombre)
            return True

    return False


def loginView(request):
    message = None

    if request.method == 'POST':
        formulario = formLogin(request.POST)
        if formulario.is_valid():
            username = request.POST['username']  # formulario.cleaned_data
            password = request.POST['password']  # formulario.cleaned_data
            user = authenticate(username=username, password=password)

            if user is not None:
                grupo = []
                if hasattr(user, 'ldap_user'):
                    # active directory

                    if grupo_check(user, grupo):
                        if user.is_active:
                            login(request, user)
                            request.session['userID'] = user.id
                            request.session['nombreUsuario'] = username
                            inicializarVariables(request)

                            return render_to_response('Main.html', {'grupo': grupo},
                                                      context_instance=RequestContext(request))
                        else:
                            message = "Usuario Inactivo"
                    else:
                        message = "No tiene permisos para acceder"
                else:
                    # "No es usuario de Active directory"

                    if user.is_active:
                        login(request, user)
                        request.session['userID'] = user.id
                        request.session['nombreUsuario'] = username
                        inicializarVariables(request)

                        return render_to_response('Main.html', {'grupo': ['todo']},
                                                  context_instance=RequestContext(request))
                    else:
                        message = "Usuario Inactivo"
            else:
                message = 'Nombre de usuario y/o password incorrecto/s'
    else:
        formulario = formLogin()
    return render_to_response('inicio/login.html', {'message': message, 'formulario': formulario},
                              context_instance=RequestContext(request))


@login_required
def view_in_pdf(request):
    if (request.session['agrupacion'] == 'Totales'):  # Si se agrupa por totales quiere decir que es otro informe.
        template_name = "reportesEstadisticos/ventasMensuales/ventaMensualPDF.html"  # la sesión de agrupación se setea en totales.

        request.session[
            'titulo'] = ''  # Porque no se le puede enviar variables NuLL a pdf se setean de nuevo estos valores
        lista = request.session['lista_totales']

    elif request.session['agrupacion'] == 'Cliente':
        lista = request.session['listaCCA_Grupo']
        template_name = "reportesEstadisticos/reportesFormasPago/formasDePagoPDF.html"

    elif request.session['agrupacion'] == 'VentaNetaAnual':  # Informa de ventas anuales de publicidad

        lista = request.session['lista_resultados']
        anioanterior = lista[0]['anio']

        subtotal_directas_cms = 0
        subtotal_directas_neto_sin_iva = 0
        subtotal_capital_cms = 0
        subtotal_capital_neto_sin_iva = 0
        subtotal_interior_cms = 0
        subtotal_interior_neto_sin_iva = 0
        subtotal_ventura_cms = 0
        subtotal_ventura_neto_sin_iva = 0
        subtotal_oficiales_cms = 0
        subtotal_oficiales_neto_sin_iva = 0
        subtotal_canjes_cms = 0
        subtotal_canjes_neto_sin_iva = 0
        subtotal_contado_cms = 0
        subtotal_contado_neto_sin_iva = 0
        subtotal_total_cms = 0
        subtotal_total_neto_sin_iva = 0

        listaNueva = []
        for elemento in lista:

            if elemento['anio'] != anioanterior:
                listaNueva.append(dict(anio='', mes='', directas_cms=subtotal_directas_cms,
                                       directas_neto_sin_iva=subtotal_directas_neto_sin_iva,
                                       capital_cms=subtotal_capital_cms,
                                       capital_neto_sin_iva=subtotal_capital_neto_sin_iva,
                                       interior_cms=subtotal_interior_cms,
                                       interior_neto_sin_iva=subtotal_interior_neto_sin_iva,
                                       ventura_cms=subtotal_ventura_cms,
                                       ventura_neto_sin_iva=subtotal_ventura_neto_sin_iva,
                                       oficiales_cms=subtotal_oficiales_cms,
                                       oficiales_neto_sin_iva=subtotal_oficiales_neto_sin_iva,
                                       canjes_cms=subtotal_canjes_cms, canjes_neto_sin_iva=subtotal_canjes_neto_sin_iva,
                                       contado_cms=subtotal_contado_cms,
                                       contado_neto_sin_iva=subtotal_contado_neto_sin_iva,
                                       total_cms=subtotal_total_cms, total_neto_sin_iva=subtotal_total_neto_sin_iva))

                listaNueva.append(dict(anio='-', mes='-', directas_cms=0, directas_neto_sin_iva=0,
                                       capital_cms=0, capital_neto_sin_iva=0,
                                       interior_cms=0, interior_neto_sin_iva=0,
                                       ventura_cms=0, ventura_neto_sin_iva=0,
                                       oficiales_cms=0, oficiales_neto_sin_iva=0,
                                       canjes_cms=0, canjes_neto_sin_iva=0,
                                       contado_cms=0, contado_neto_sin_iva=0,
                                       total_cms=0, total_neto_sin_iva=0))
                listaNueva.append(elemento)
            else:
                listaNueva.append(elemento)

            subtotal_directas_cms = subtotal_directas_cms + elemento['directas_cms']
            subtotal_directas_neto_sin_iva = subtotal_directas_neto_sin_iva + elemento['directas_neto_sin_iva']
            subtotal_capital_cms = subtotal_capital_cms + elemento['capital_cms']
            subtotal_capital_neto_sin_iva = subtotal_capital_neto_sin_iva + elemento['capital_neto_sin_iva']
            subtotal_interior_cms = subtotal_interior_cms + elemento['interior_cms']
            subtotal_interior_neto_sin_iva = subtotal_interior_neto_sin_iva + elemento['interior_neto_sin_iva']
            subtotal_ventura_cms = subtotal_ventura_cms + elemento['ventura_cms']
            subtotal_ventura_neto_sin_iva = subtotal_ventura_neto_sin_iva + elemento['ventura_neto_sin_iva']
            subtotal_oficiales_cms = subtotal_oficiales_cms + elemento['oficiales_cms']
            subtotal_oficiales_neto_sin_iva = subtotal_oficiales_neto_sin_iva + elemento['oficiales_neto_sin_iva']
            subtotal_canjes_cms = subtotal_canjes_cms + elemento['canjes_cms']
            subtotal_canjes_neto_sin_iva = subtotal_canjes_neto_sin_iva + elemento['canjes_neto_sin_iva']
            subtotal_contado_cms = subtotal_contado_cms + elemento['contado_cms']
            subtotal_contado_neto_sin_iva = subtotal_contado_neto_sin_iva + elemento['contado_neto_sin_iva']
            subtotal_total_cms = subtotal_total_cms + elemento['total_cms']
            subtotal_total_neto_sin_iva = subtotal_total_neto_sin_iva + elemento['total_neto_sin_iva']

            anioanterior = elemento['anio']

        lista = listaNueva
        request.session['titulo'] = ''
        request.session['fechaDesde'] = ''
        request.session['fechaHasta'] = ''
        # request.session['codigoRemoto'] = ''
        template_name = "reportesEstadisticos/ventaNetaAnual/ventaNetaAnualPDF.html"
        # Las fechas y el codigo remoto no se ocupan aún en este pdf.

    else:
        lista = request.session['lista_ccA']
        template_name = "reportesEstadisticos/reportesFormasPago/formasDePagoPDF.html"

    context_dict = {

        'object_lists': lista,  # Aqui es donde llamo a las variables de sesion
        'nombreUsuario': request.session['nombreUsuario'],
        'agrupacion': request.session['agrupacion'],
        'titulo': request.session['titulo'],
        'fechaDesde': request.session['fechaDesde'],
        'fechaHasta': request.session['fechaHasta'],
        'provincia': request.session['codigoRemoto']
    }
    context_dict.update({'pagesize': 'A4'})

    template = get_template(template_name)
    context = Context(context_dict)
    html = template.render(context)
    result = StringIO.StringIO()

    links = lambda uri, rel: os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ''))
    pisa.CreatePDF(html.encode("UTF-8"), result, encoding='UTF-8', link_callback=links)

    try:
        return HttpResponse(result.getvalue(), content_type='application/pdf')

        """ Habilitar si se quiere generar un archivo nuevo y enviar por mail """
        # response = HttpResponse(result.getvalue(), mimetype='application/pdf')
        # response['Content-Disposition'] = 'attachment; filename=output.pdf'
        # #return response
        #
        # email = EmailMessage('Enviando PDF', 'Mateo aca va el pdf que cree recien', to=['mateobasaldua@gmail.com'])
        # email.attach('output.pdf', result.getvalue(), 'application/pdf')
        # email.send()
        # return HttpResponseRedirect('/')
    except:
        return HttpResponse('Tuvimos algunos errores<pre>%s</pre>' % escape(html))


def fetch_resources(uri, rel):
    """ Access files and images."""
    path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
    return path


@login_required
def viewToXls(request):
    resguardoTitulo = request.session['titulo']
    if "-" in resguardoTitulo:
        resguardoTitulo = 'OtrasFormasDePago'

    elif request.session['titulo'] == 'Ventas Netas Anuales de Publicidad' or resguardoTitulo == 'V N A de Publicidad':
        resguardoTitulo = 'V N A de Publicidad'
        request.session['titulo'] = 'Ventas Netas Anuales de Publicidad'

    if request.session['codigoRemoto'] == 0:
        titulo = (request.session['titulo'])
    else:
        titulo = (request.session['titulo'] + ' - ' + request.session['codigoRemoto'])  # .replace(' ', '_')

    titulo = titulo.replace('_-_', '-')
    if request.session['fechaDesde'] == 0 and request.session['fechaHasta'] == 0:
        tituloCompleto = titulo
    else:
        tituloCompleto = titulo + ' - De: ' + request.session['fechaDesde'] + ' - Hasta: ' + request.session[
            'fechaHasta']

    book = xlwt.Workbook(encoding='utf8')

    sheet = book.add_sheet(resguardoTitulo[0:18], cell_overwrite_ok=True)  # book.add_sheet('Cta. Corriente')
    # Adding style for cell
    # Create Alignment
    alignment = xlwt.Alignment()
    alignmentDer = xlwt.Alignment()
    # horz May be: HORZ_GENERAL, HORZ_LEFT, HORZ_CENTER, HORZ_RIGHT,
    # HORZ_FILLED, HORZ_JUSTIFIED, HORZ_CENTER_ACROSS_SEL,
    # HORZ_DISTRIBUTED
    alignment.horz = xlwt.Alignment.HORZ_LEFT
    alignmentDer.horz = xlwt.Alignment.HORZ_RIGHT
    # May be: VERT_TOP, VERT_CENTER, VERT_BOTTOM, VERT_JUSTIFIED,
    # VERT_DISTRIBUTED
    alignment.vert = xlwt.Alignment.VERT_CENTER
    alignmentDer.vert = xlwt.Alignment.VERT_CENTER
    style = xlwt.XFStyle()  # Create Style
    style.alignment = alignment  # Add Alignment to Style

    borders = xlwt.Borders()
    borders.left = 1
    borders.right = 1
    borders.top = 1
    borders.bottom = 1

    style.borders = borders


    # titulo
    fuenteTit = xlwt.Font()
    fuenteTit.underline = True
    # para modificar el size lo hacemos con height pero debemos saber el size que queremos y hace valor lo multiplicamos por 20. en nuestro caso el size es 14
    fuenteTit.height = 20 * 14
    alignmentCenter = xlwt.Alignment()
    alignmentCenter.horz = xlwt.Alignment.HORZ_CENTER
    alignmentCenter.vert = xlwt.Alignment.VERT_CENTER
    estiloTit = xlwt.XFStyle()
    estiloTit.font = fuenteTit
    estiloTit.alignment = alignmentCenter

    keys = request.session['keys']

    estiloDer = xlwt.XFStyle()
    estiloDer.alignment = alignmentDer

    xlwt.add_palette_colour("custom_colour", 0x21)
    book.set_colour_RGB(0x21, 205, 222, 205)

    estiloHead = xlwt.easyxf(
        'pattern: pattern solid, fore_colour custom_colour; alignment: horiz centre; font: bold off, height 210; borders: left medium; borders: top medium; borders: bottom medium; borders: right medium',
        num_format_str="0.0")  #
    estiloUltimaFila = xlwt.easyxf(
        'pattern: pattern solid, fore_colour custom_colour; alignment: horiz right; font: bold off, colour_index 4; borders: left 1; borders: top 1; borders: bottom 1; borders: right 1')  #
    estiloUltimaFilaStr = xlwt.easyxf(
        'pattern: pattern solid, fore_colour custom_colour; alignment: horiz left; font: bold off, colour_index 4; borders: left 1; borders: top 1; borders: bottom 1; borders: right 1')  #
    estiloDerecho = xlwt.easyxf('alignment: horiz right; font: bold off')  #

    fuente = xlwt.Font()
    fuente.name = 'Arial'
    # 1:blanco 2:Rojo 3:verdeClaro 4:Azul  5:
    fuente.colour_index = 8
    fuente.bold = True
    estilo0 = xlwt.XFStyle()
    estilo0.alignment = alignment  #Alineacion creada mas arriba
    estilo0.font = fuente

    estilo1 = xlwt.XFStyle()
    estilo1.num_format_str = 'DD-MMM-YYYY'
    estilo1.alignment = alignment

    estiloFecha = xlwt.XFStyle()
    estiloFecha.num_format_str = 'DD-MMM-YYYY'
    estiloFecha.alignment = alignment

    estiloFecha.borders = borders

    estilo2 = xlwt.XFStyle()
    estilo2.num_format_str = 'HH:MM'
    estilo2.alignment = alignment

    data = request.session['data']  #data es una lista de diccionarios traidos con la función de la Bd SQlServer

    usuario = 'Por usuario: ', (
        request.user).username  #siempre tengo que pedir el request del usuario para obtener sus datos.



    # Agrego aca recien los margenes porque sino me escribe fecha y hora con recuadro
    estiloDer.borders = borders

    #a continuacion voy a combinar celdas para escribir el titulo.
    sheet.write_merge(4, 4, 0, (len(keys) - 1), tituloCompleto, estiloTit)  #'Informe Cuenta Corriente en Bruto'

    #variable para especificar si a una columna especial queremos darle un poco mas de width
    agrandarColumna = 0

    header = request.session['headers']
    for hcol, hcol_data in enumerate(header):
        if 'Promoci' in hcol_data:
            agrandarColumna = hcol
        sheet.write(6, hcol, hcol_data, estiloHead)

    if agrandarColumna != 0:
        sheet.col(agrandarColumna).width = 256 * 30

    ultimaFila = 6
    if (len(keys) == 3):
        sheet.col(0).width = 256 * 30
        sheet.col(
            1).width = 256 * 30  #con este código supongo cambiar el tamaño de de la columna 2, arrancando a contar de 0.
        sheet.col(2).width = 256 * 30

        sheet.write(0, 1, "Fuente: Sistema de Reportes de Pasantes (SiRePa)", estilo0)
        sheet.write(0, 3, usuario, estilo0)

        sheet.write(1, 1, 'Emitido el:', estiloDerecho)
        sheet.write(1, 2, datetime.datetime.now(), estilo1)
        sheet.write(1, 3, 'Hora:', estiloDerecho)
        sheet.write(1, 4, datetime.datetime.now(), estilo2)

        for i, row_data in enumerate(data, start=7):  # start from row no.6
            ultimaFila += 1
            for j, col in enumerate(keys):

                e = row_data[col]

                if col == 'Grupo' and e == 0:
                    sheet.write(i, j, 'Registro/s indefindo/s y/o sin Grupo', style)


                elif e == 99:
                    sheet.write(i, j, 'Contado', style)
                elif e == 3:
                    sheet.write(i, j, 'Interior', style)
                elif e == 4:
                    sheet.write(i, j, 'Capital', style)
                elif e == 5:
                    sheet.write(i, j, 'Ventura', style)
                elif e == 6:
                    sheet.write(i, j, 'Oficiales', style)
                elif e == 7:
                    sheet.write(i, j, 'Canjes', style)
                elif e == 9:
                    sheet.write(i, j, 'Directas', style)
                elif e == 8000:
                    sheet.write(i, j, 'Totales:', style)
                elif e == 'algo':
                    sheet.write(i, j, '', style)
                elif e == '':
                    sheet.write(i, j, '', style)
                else:
                    sheet.write(i, j, e, estiloDer)

        #con esto obtengo el último elemento de mi lista de data, porque voy incrementando con ultimaFila y le resto donde comienza la data (7) que este valor es estático
        ultimoElemento = dict(data[ultimaFila - 7])
        for hcol, hcol_data in enumerate(keys):
            if hcol_data == 'Grupo' and ultimoElemento[hcol_data] == 8000:
                sheet.write(ultimaFila, hcol, 'Totales:                      ', estiloUltimaFila)
            else:
                sheet.write(ultimaFila, hcol, ultimoElemento[hcol_data], estiloUltimaFila)
                # elif tituloCompleto == 'V_N_A_de_Publicidad-Chaco':



    else:

        if resguardoTitulo != 'V N A de Publicidad':
            if len(keys) <= 6:
                sheet.col(1).width = 256 * 28
                sheet.col(2).width = 256 * 28
                sheet.col(3).width = 256 * 28
                sheet.col(4).width = 256 * 28
                sheet.col(5).width = 256 * 28
                sheet.write(0, 4, usuario, estilo0)
            else:
                sheet.write(0, 6, usuario, estilo0)

            sheet.col(0).width = 256 * 26
            # sheet.col(
            #     2).width = 256 * 10  #con este código supongo cambiar el tamaño de de la columna 2, arrancando a contar de 0.
            # sheet.col(21).width = 256 * 21

            sheet.write(0, 1, "Fuente: Sistema de Reportes de Pasantes (SiRePa)", estilo0)

            sheet.write(1, 1, 'Emitido el:', estiloDerecho)
            sheet.write(1, 2, datetime.now(), estilo1)
            sheet.write(1, 3, 'Hora:', estiloDerecho)
            sheet.write(1, 4, datetime.now(), estilo2)

            marcarFilaConTotales = 0
            for i, row_data in enumerate(data, start=7):  # start from row no.6
                for j, col in enumerate(keys):
                    e = row_data[col]
                    if request.session['reporteConTotales'] != 0 and (i - request.session['reporteConTotales']) == 6:
                        if isinstance(e, float) or isinstance(e, int):
                            sheet.write(i, j, round(float(e), 2), estiloUltimaFila)
                        else:
                            sheet.write(i, j, e, estiloUltimaFilaStr)
                    elif col == 'horaCaptura' and isinstance(e, int):
                        e1 = int(e) + 1
                        n = str(e) + ' (de ' + str(e) + ' a ' + str(e1) + ')'
                        # pprint.pprint(n)
                        sheet.write(i, j, n, style)
                    elif isinstance(e, str) and 'Total' in e:
                        marcarFilaConTotales = i
                        sheet.write(i, j, e, estiloUltimaFilaStr)
                    elif marcarFilaConTotales != 0 and marcarFilaConTotales == i:
                        if isinstance(e, float) or isinstance(e, int):
                            sheet.write(marcarFilaConTotales, j, round(e, 2), estiloUltimaFila)
                        else:
                            sheet.write(marcarFilaConTotales, j, e, estiloUltimaFilaStr)

                    elif isinstance(e, float) or isinstance(e, int):
                        if col == 'anio':
                            sheet.write(i, j, e, style)
                        elif e == 0:
                            sheet.write(i, j, '-', estiloDer)
                        else:
                            sheet.write(i, j, round(float(e), 2), estiloDer)
                    else:

                        if 'fecha' in col or 'Fecha' in col:

                            sheet.write(i, j, datetime.strptime(str(e.date()), '%Y-%m-%d'), estiloFecha)
                        else:
                            sheet.write(i, j, e, style)

        else:
            sheet.col(0).width = 256 * 10
            sheet.col(
                1).width = 256 * 10  #con este código supongo cambiar el tamaño de de la columna 2, arrancando a contar de 0.
            # sheet.col(21).width = 256 * 21

            sheet.write(0, 2, "Fuente: Sistema de Reportes de Pasantes (SiRePa)", estilo0)
            sheet.write(0, 7, usuario, estilo0)
            sheet.write(1, 2, 'Emitido el:', estiloDerecho)
            sheet.write(1, 3, datetime.now(), estilo1)
            sheet.write(1, 5, 'Hora:', estiloDerecho)
            sheet.write(1, 6, datetime.now(), estilo2)

            comienzoDeFilas = 6
            cantAnios = 0
            while len(data) > cantAnios:

                anio = data[cantAnios]['anio']
                iterAnio = data[cantAnios]['anio']

                directas_cms = 0
                directas_neto_sin_iva = 0
                capital_cms = 0
                capital_neto_sin_iva = 0
                interior_cms = 0
                interior_neto_sin_iva = 0
                ventura_cms = 0
                ventura_neto_sin_iva = 0
                oficiales_cms = 0
                oficiales_neto_sin_iva = 0
                canjes_cms = 0
                canjes_neto_sin_iva = 0
                contado_cms = 0
                contado_neto_sin_iva = 0
                total_cms = 0
                total_neto_sin_iva = 0

                while iterAnio == anio:

                    comienzoDeFilas += 1
                    col = 0
                    # ['anio', 'mes', 'directas_cms', 'directas_neto_sin_iva', 'capital_cms',
                    #            'capital_neto_sin_iva', 'interior_cms', 'interior_neto_sin_iva',
                    #            'ventura_cms', 'ventura_neto_sin_iva', 'oficiales_cms', 'oficiales_neto_sin_iva',
                    #            'canjes_cms', 'canjes_neto_sin_iva', 'contado_cms',
                    #            'contado_neto_sin_iva', 'total_cms', 'total_neto_sin_iva']

                    for key in keys:  # start from row no.6

                        if key == 'directas_cms':
                            directas_cms += data[cantAnios][key]
                        elif key == 'directas_neto_sin_iva':
                            directas_neto_sin_iva += data[cantAnios][key]
                        elif key == 'capital_cms':
                            capital_cms += data[cantAnios][key]
                        elif key == 'capital_neto_sin_iva':
                            capital_neto_sin_iva += data[cantAnios][key]
                        elif key == 'interior_cms':
                            interior_cms += data[cantAnios][key]
                        elif key == 'interior_neto_sin_iva':
                            interior_neto_sin_iva += data[cantAnios][key]
                        elif key == 'directas_neto_sin_iva':
                            directas_neto_sin_iva += data[cantAnios][key]
                        elif key == 'ventura_cms':
                            ventura_cms += data[cantAnios][key]
                        elif key == 'ventura_neto_sin_iva':
                            ventura_neto_sin_iva += data[cantAnios][key]
                        elif key == 'oficiales_cms':
                            oficiales_cms += data[cantAnios][key]
                        elif key == 'oficiales_neto_sin_iva':
                            oficiales_neto_sin_iva += data[cantAnios][key]
                        elif key == 'canjes_cms':
                            canjes_cms += data[cantAnios][key]
                        elif key == 'canjes_neto_sin_iva':
                            canjes_neto_sin_iva += data[cantAnios][key]
                        elif key == 'contado_cms':
                            contado_cms += data[cantAnios][key]
                        elif key == 'contado_neto_sin_iva':
                            contado_neto_sin_iva += data[cantAnios][key]
                        elif key == 'total_cms':
                            total_cms += data[cantAnios][key]
                        elif key == 'total_neto_sin_iva':
                            total_neto_sin_iva += data[cantAnios][key]

                        celda = data[cantAnios][key]

                        if isinstance(celda, float) or isinstance(celda, int):
                            if key == 'anio':
                                sheet.write(comienzoDeFilas, col, celda, style)
                            elif celda == 0:
                                sheet.write(comienzoDeFilas, col, '-', estiloDer)
                            elif (isinstance(celda, int)):
                                sheet.write(comienzoDeFilas, col, round(celda, 2), estiloDer)
                            else:
                                sheet.write(comienzoDeFilas, col, round(float(celda), 2), estiloDer)
                        else:
                            sheet.write(comienzoDeFilas, col, celda, style)
                        col += 1

                    cantAnios += 1
                    if cantAnios <= (len(data) - 1):
                        iterAnio = data[cantAnios]['anio']
                    else:
                        iterAnio = 1

                comienzoDeFilas += 1
                listaSubTotales = [directas_cms, directas_neto_sin_iva, capital_cms, capital_neto_sin_iva, interior_cms,
                                   interior_neto_sin_iva,
                                   ventura_cms, ventura_neto_sin_iva, oficiales_cms, oficiales_neto_sin_iva, canjes_cms,
                                   canjes_neto_sin_iva, contado_cms,
                                   contado_neto_sin_iva, total_cms, total_neto_sin_iva]
                sheet.write_merge(comienzoDeFilas, comienzoDeFilas, 0, 1, 'Totales             ', estiloUltimaFila)
                for j, subTotal in enumerate(listaSubTotales, start=2):
                    sheet.write(comienzoDeFilas, j, float(subTotal), estiloUltimaFila)

                comienzoDeFilas += 2


    #pongo aca la imagen porque arriba se agranda mucho
    # sheet.write_merge(0, 2, 0, 0)
    sheet.insert_bitmap(IMAGEN_EXCEL, 0, 0)

    response = HttpResponse(content_type='application/vnd.ms-excel')

    tituloCompleto = tituloCompleto.replace(' ', '_')
    tituloCompleto = tituloCompleto.replace('_-_', '-')
    response['Content-Disposition'] = 'attachment; filename=' + tituloCompleto + ''
    book.save(response)
    return response


def logoutView(request):
    auth.logout(request)
    # Redirect to a success page.
    return HttpResponseRedirect("/")


def dictfetchall(cursor):
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]


@login_required
def json_test(request):
    results = request.session['lista_resultados']

    request.session['titulo'] = 'Cuenta_Corriente'

    request.session['data'] = results

    request.session['headers'] = ['Ag. Cliente', 'Codigo', 'Aviso', 'Cms', 'V. Anuncio', 'Recargo color',
                                  'Recargo Logo',
                                  'Desc. Prom', 'Desc. Convenio', 'Desc Agencia', 'Desc. a Mano', 'F. factura',
                                  'Nº factura', 'Nº pedido',
                                  'Cod. Aviso', 'Ord. Publicidad', 'Valor Sin Imp.', 'Cond. Imp.', 'Valor a Pagar',
                                  'SupSaCh', 'cms_puro',
                                  'Nombre']

    request.session['keys'] = ['AgenciaCliente', 'Codigo', 'Aviso', 'centimetros', 'ValorAnuncio', 'RecargoColor',
                               'RecargoLogo', 'DescPromocion', 'DescConvenio', 'DescAgencia', 'DescuentoAMano',
                               'fechafactura', 'nrofactura', 'nropedido', 'CodigoAviso', 'OrdenPublicidad',
                               'ValorSinImpuestos', 'CondImpuesto', 'valorapagar', 'SupSaCh', 'cms_puro', 'nombre']

    jsony = json.dumps(results)

    return HttpResponse(jsony, content_type='application/json')


@login_required
def json_testA(request):
    results = request.session['lista_ccA']

    # request.session['titulo'] = 'Cuenta Corriente A'



    request.session['data'] = results

    if request.session['titulo'] == 'Contado':
        request.session['headers'] = ['Ag. Cliente', 'Aviso', 'Total Cms', 'Desc Cms', 'Cms Neto', 'V. Anuncio',
                                      'Rec. Color',
                                      'Rec. Logo', 'Desc. Manual', 'Tot. Recargo', 'Tot. Bruto', 'Desc. Promocion',
                                      'Desc. Convenio',
                                      'Com Agencia', 'Desc. Agencia', 'Total Desc.', 'Neto Sin Iva', 'Fecha Factura',
                                      'Nº Factura', 'Nº Pedido', 'Cod Aviso']

        request.session['keys'] = ['AgenciaCliente', 'Aviso', 'TotalCms', 'DescCms', 'CmsNeto', 'ValorAnuncio',
                                   'RecargoColor', 'RecargoLogo', 'DescManual', 'TotalRecargo', 'TotalBruto',
                                   'DescPromocion', 'DescConvenio', 'ComAgencia', 'DescAgencia', 'TotalDescuento',
                                   'NetoSinIva', 'fechafactura', 'nrofactura', 'nropedido', 'CodigoAviso']
    else:
        request.session['headers'] = ['Ag. Cliente', 'Codigo', 'Aviso', 'Total Cms', 'Desc Cms', 'Cms Neto',
                                      'V. Anuncio',
                                      'Rec. Color',
                                      'Rec. Logo', 'Desc. Manual', 'Tot. Recargo', 'Tot. Bruto', 'Desc. Promocion',
                                      'Desc. Convenio',
                                      'Com Agencia', 'Desc. Agencia', 'Total Desc.', 'Neto Sin Iva', 'Fecha Factura',
                                      'Nº Factura', 'Nº Pedido', 'Cod Aviso', 'Orden Publicidad']

        request.session['keys'] = ['AgenciaCliente', 'Codigo', 'Aviso', 'TotalCms', 'DescCms', 'CmsNeto',
                                   'ValorAnuncio',
                                   'RecargoColor', 'RecargoLogo', 'DescManual', 'TotalRecargo', 'TotalBruto',
                                   'DescPromocion', 'DescConvenio', 'ComAgencia', 'DescAgencia', 'TotalDescuento',
                                   'NetoSinIva', 'fechafactura', 'nrofactura', 'nropedido', 'CodigoAviso',
                                   'OrdenPublicidad']

    jsony = json.dumps(results)
    return HttpResponse(jsony, content_type='application/json')


@login_required
def json_testGrupo(request):
    results = request.session['listaCCA_Grupo']

    request.session['data'] = results

    request.session['headers'] = ['Aviso', 'Total Cms', 'Desc Cms', 'Cms Neto', 'V. Anuncio', 'Rec. Color', 'Rec. Logo',
                                  'Desc. Manual',
                                  'Tot. Recargo', 'Tot. Bruto', 'Desc. Promocion', 'Desc. Convenio', 'Com Agencia',
                                  'Desc. Agencia',
                                  'Total Desc.', 'Neto Sin Iva', 'Fecha Factura', 'Nº Factura', 'Nº Pedido',
                                  'Cod Aviso', 'Orden Publicidad']

    request.session['keys'] = ['Aviso', 'TotalCms', 'DescCms', 'CmsNeto', 'ValorAnuncio', 'RecargoColor', 'RecargoLogo',
                               'DescManual', 'TotalRecargo', 'TotalBruto', 'DescPromocion', 'DescConvenio',
                               'ComAgencia', 'DescAgencia', 'TotalDescuento', 'NetoSinIva', 'fechafactura',
                               'nrofactura', 'nropedido', 'CodigoAviso', 'OrdenPublicidad']

    jsony = json.dumps(results)
    return HttpResponse(jsony, content_type='application/json')


@login_required
def json_totales(request):
    results = request.session['lista_totales']

    # variables de sesión necesarias para hacer el excel del grid totales

    request.session['data'] = results

    request.session['headers'] = ['Grupo', 'Centímetros', 'Neto sin Iva']

    request.session['titulo'] = 'Totales Publicidad'

    request.session['keys'] = ['Grupo', 'TotalCms', 'NetoSinIva']

    jsony = json.dumps(results)
    return HttpResponse(jsony, content_type='application/json')


def json_ventasNetasAnuales(request):
    listaTotal = request.session['lista_resultados']

    request.session['data'] = listaTotal

    request.session['headers'] = ['Año', 'Mes', 'DirectasCms', 'DirectasNetoSinIva', 'CapitalCms', 'CapitalNetoSinIva',
                                  'InteriorCms', 'InteriorNetoSinIva',
                                  'VenturaCms', 'VenturaNetoSinIva', 'OficialesCms', 'OficialesNetoSinIva', 'CanjesCms',
                                  'CanjesNetoSinIva', 'ContadoCms',
                                  'ContadoNetoSinIva', 'TotalCms', 'TotalNetoSinIva']

    request.session['titulo'] = 'V N A de Publicidad'

    request.session['fechaDesde'] = 0
    request.session['fechaHasta'] = 0

    request.session['keys'] = ['anio', 'mes', 'directas_cms', 'directas_neto_sin_iva', 'capital_cms',
                               'capital_neto_sin_iva', 'interior_cms', 'interior_neto_sin_iva',
                               'ventura_cms', 'ventura_neto_sin_iva', 'oficiales_cms', 'oficiales_neto_sin_iva',
                               'canjes_cms', 'canjes_neto_sin_iva', 'contado_cms',
                               'contado_neto_sin_iva', 'total_cms', 'total_neto_sin_iva']

    jsony = json.dumps(listaTotal)
    return HttpResponse(jsony, content_type='application/json')


def json_graficostotales(request):
    results = request.session['lista_grafico_recydesc']
    jsony = json.dumps(results)
    return HttpResponse(jsony, content_type='application/json')


def json_graficosFormasDePagoPorCms(request):
    results = request.session['listaParaGraficosPorFormasDePago']
    jsony = json.dumps(results)
    return HttpResponse(jsony, content_type='application/json')


def jsonPromociones(request):
    results = request.session['listaPromociones']

    promocionesSinConvenios = []
    for data in results:
        if data['ValorAuxiliar'] != 'Convenio':
            promocionesSinConvenios.append(data)

    request.session['data'] = promocionesSinConvenios

    request.session['headers'] = ['Ag. Cliente', 'Aviso', 'Cms Neto', 'V. Anuncio', 'Tot. Bruto', 'Total Desc.',
                                  'Neto Sin Iva', 'Promoción', 'F. Factura', 'Nº Factura', 'Nº Pedido', 'Cod. Aviso',
                                  'Orden Publicidad']

    request.session['titulo'] = 'Promociones'

    request.session['keys'] = ['AgenciaCliente', 'Aviso', 'CmsNeto', 'ValorAnuncio', 'TotalBruto', 'TotalDescuento',
                               'NetoSinIva', 'ValorAuxiliar', 'fechafactura', 'nrofactura', 'nropedido', 'CodigoAviso',
                               'OrdenPublicidad']

    jsony = json.dumps(promocionesSinConvenios)
    return HttpResponse(jsony, content_type='application/json')


def jsonCapturadoresIva(request):
    result = request.session['data']
    resultGrid = []
    for data in result:
        data.pop('fechaHoraCaptura', None)
        resultGrid.append(data)


    #########   Variables para Excel    ################################


    request.session['keys'] = ["AgenciaCliente", "CodigoAviso", "Aviso", "centimetros", "ValorSinImpuestos",
                               "fechaHoraCaptura", "OrdenPublicidad", "nombre", "TasaIVA", "NombreUsuario", 'revision']

    request.session['headers'] = ["Agencia Cliente", "Cod Aviso", "Aviso", "Centimetros", "Valor sin Imp", "Captura",
                                  "Orden Publicidad", "Forma de Pago", "Tasa IVA", "Nombre Usuario", 'Revision']

    #########################################################
    jsony = json.dumps(resultGrid)
    return HttpResponse(jsony, content_type='application/json')


@login_required
def listaCtaCteA(request):
    return render_to_response('reportesEstadisticos/reportesFormasPago/listaCtaCteA.html',
                              context_instance=RequestContext(request))


def cuentaCorrienteB(request):
    return render_to_response('reportesEstadisticos/reportesFormasPago/cuentaCorrienteBruto.html',
                              {'lista': request.session['lista_resultados']},
                              context_instance=RequestContext(request))


@login_required
def cuentaCorrienteA(request):
    listaCuentaCorriente = request.session['lista_ccA']
    request.session['reporteConTotales'] = 0
    if request.method == 'POST' and request.is_ajax():

        agrupacion = request.POST["agrupacion"]
        tit = request.POST["tit"]

        # 1: tipo de Aviso     ---------------------  2: Tipo de cliente  -------------- 3: No resumido
        if agrupacion == u'1':

            listaCuentaCorrienteOrdenada = sorted(listaCuentaCorriente, key=operator.itemgetter('Aviso'))
            listaCuentaCorrientePorAviso = []
            Total_TotalCms = 0
            Total_DescCms = 0
            Total_CmsNeto = 0
            Total_TotalBruto = 0
            Total_TotalDescuento = 0
            Total_NetoSinIva = 0
            for key, val in itertools.groupby(listaCuentaCorrienteOrdenada, lambda v: v['Aviso']):
                TotalCms = sum(item['TotalCms'] for item in val)
                Total_TotalCms += TotalCms
                # aca creo la lista por primera vez con los N tipo de avisos que existen
                listaCuentaCorrientePorAviso.append({'Aviso': key, 'TotalCms': TotalCms})

            i = 0
            for key, val in itertools.groupby(listaCuentaCorrienteOrdenada, lambda v: v['Aviso']):
                DescCms = sum(item['DescCms'] for item in val)
                Total_DescCms += DescCms
                listaCuentaCorrientePorAviso[i].update({'DescCms': DescCms})
                i += 1

            i = 0
            for key, val in itertools.groupby(listaCuentaCorrienteOrdenada, lambda v: v['Aviso']):
                CmsNeto = sum(item['CmsNeto'] for item in val)
                Total_CmsNeto += CmsNeto
                listaCuentaCorrientePorAviso[i].update({'CmsNeto': CmsNeto})
                i += 1

            i = 0
            for key, val in itertools.groupby(listaCuentaCorrienteOrdenada, lambda v: v['Aviso']):
                TotalBruto = sum(item['TotalBruto'] for item in val)
                Total_TotalBruto += TotalBruto
                listaCuentaCorrientePorAviso[i].update({'TotalBruto': TotalBruto})
                i += 1

            i = 0
            for key, val in itertools.groupby(listaCuentaCorrienteOrdenada, lambda v: v['Aviso']):
                TotalDescuento = sum(item['TotalDescuento'] for item in val)
                Total_TotalDescuento += TotalDescuento
                listaCuentaCorrientePorAviso[i].update({'TotalDescuento': TotalDescuento})
                i += 1

            i = 0
            for key, val in itertools.groupby(listaCuentaCorrienteOrdenada, lambda v: v['Aviso']):
                NetoSinIva = sum(item['NetoSinIva'] for item in val)
                Total_NetoSinIva += NetoSinIva
                listaCuentaCorrientePorAviso[i].update({'NetoSinIva': NetoSinIva})
                i += 1

            # # Se agrega esta línea para ordenar los registros de manera ascendente.
            listaCuentaCorrientePorAviso = sorted(listaCuentaCorrientePorAviso, key=lambda k: k['TotalCms'],
                                                  reverse=True)

            total_porcentajeTotalCms = 0
            total_porcentajeNetoSinIva = 0
            for data in listaCuentaCorrientePorAviso:
                porcentajeTotalCms = 0
                if Total_TotalCms != 0:
                    porcentajeTotalCms = (data['TotalCms'] / Total_TotalCms) * 100
                    total_porcentajeTotalCms += porcentajeTotalCms

                porcentajeNetoSinIva = 0
                if Total_NetoSinIva != 0:
                    porcentajeNetoSinIva = (data['NetoSinIva'] / Total_NetoSinIva) * 100
                    total_porcentajeNetoSinIva += porcentajeNetoSinIva

                data.update({'PorcentajeCms': porcentajeTotalCms, 'PorcentajeNetoSinIva': porcentajeNetoSinIva})

            listaCuentaCorrientePorAviso.append(
                {'Aviso': '', 'TotalCms': '', 'DescCms': '', 'CmsNeto': '', 'TotalBruto': '',
                 'TotalDescuento': '', 'NetoSinIva': '', 'PorcentajeCms': '', 'PorcentajeNetoSinIva': ''})

            listaCuentaCorrientePorAviso.append(
                {'Aviso': 'Total General', 'TotalCms': Total_TotalCms, 'DescCms': Total_DescCms,
                 'CmsNeto': Total_CmsNeto, 'TotalBruto': Total_TotalBruto,
                 'TotalDescuento': Total_TotalDescuento, 'NetoSinIva': Total_NetoSinIva,
                 'PorcentajeCms': total_porcentajeTotalCms, 'PorcentajeNetoSinIva': total_porcentajeNetoSinIva})


            ##################   Cargo las variables de session necesarias para hacer el excel       #################
            request.session['data'] = listaCuentaCorrientePorAviso

            request.session['headers'] = ['Aviso', 'TotalCms', 'Desc Cms', 'Cms Neto', 'Total Bruto',
                                          'Total Descuento', 'Neto Sin Iva', '% Cms', '% Neto Sin Iva']
            if tit == u'Contado':
                request.session['titulo'] = 'Avisos de Contado'
            elif tit == u'Cuenta':
                request.session['titulo'] = 'Avisos de Cuenta Corriente'
            else:
                request.session['titulo'] = 'Avisos de ' + tit
            # las variables de las fechas no las cargo porque ya las cargo cuando hago la consulta
            # request.session['fechaDesde'] = 0
            # request.session['fechaHasta'] = 0

            request.session['reporteConTotales'] = len(listaCuentaCorrientePorAviso)

            request.session['keys'] = ['Aviso', 'TotalCms', 'DescCms', 'CmsNeto', 'TotalBruto',
                                       'TotalDescuento', 'NetoSinIva', 'PorcentajeCms', 'PorcentajeNetoSinIva']

            # pprint.pprint(listaCuentaCorrientePorAviso)
            listaCuentaCorrientePorAviso = json.dumps(listaCuentaCorrientePorAviso, cls=DjangoJSONEncoder)
            return HttpResponse(
                json.dumps({'agrupacion': agrupacion, 'listaCuentaCorrientePorAviso': listaCuentaCorrientePorAviso}),
                content_type='application/javascript')  # reemplazo el simplejason x json

        elif agrupacion == u'2':
            # ##### Hacemos lo mismo que arriba pero ahora ordenamos por Tipo de Cliente ##################################

            listaCuentaCorrienteOrdenada = sorted(listaCuentaCorriente, key=operator.itemgetter('Grupo'))
            listaCuentaCorrientePorCliente = []
            Total_TotalCms = 0
            Total_DescCms = 0
            Total_CmsNeto = 0
            Total_TotalBruto = 0
            Total_TotalDescuento = 0
            Total_NetoSinIva = 0
            for key, val in itertools.groupby(listaCuentaCorrienteOrdenada, lambda v: v['Grupo']):
                TotalCms = sum(item['TotalCms'] for item in val)
                Total_TotalCms += TotalCms
                # aca creo la lista por primera vez con los N tipo de avisos que existen
                listaCuentaCorrientePorCliente.append({'Grupo': key, 'TotalCms': TotalCms})

            i = 0
            for key, val in itertools.groupby(listaCuentaCorrienteOrdenada, lambda v: v['Grupo']):
                DescCms = sum(item['DescCms'] for item in val)
                Total_DescCms += DescCms
                listaCuentaCorrientePorCliente[i].update({'DescCms': DescCms})
                i += 1

            i = 0
            for key, val in itertools.groupby(listaCuentaCorrienteOrdenada, lambda v: v['Grupo']):
                CmsNeto = sum(item['CmsNeto'] for item in val)
                Total_CmsNeto += CmsNeto
                listaCuentaCorrientePorCliente[i].update({'CmsNeto': CmsNeto})
                i += 1

            i = 0
            for key, val in itertools.groupby(listaCuentaCorrienteOrdenada, lambda v: v['Grupo']):
                TotalBruto = sum(item['TotalBruto'] for item in val)
                Total_TotalBruto += TotalBruto
                listaCuentaCorrientePorCliente[i].update({'TotalBruto': TotalBruto})
                i += 1

            i = 0
            for key, val in itertools.groupby(listaCuentaCorrienteOrdenada, lambda v: v['Grupo']):
                TotalDescuento = sum(item['TotalDescuento'] for item in val)
                Total_TotalDescuento += TotalDescuento
                listaCuentaCorrientePorCliente[i].update({'TotalDescuento': TotalDescuento})
                i += 1

            i = 0
            for key, val in itertools.groupby(listaCuentaCorrienteOrdenada, lambda v: v['Grupo']):
                NetoSinIva = sum(item['NetoSinIva'] for item in val)
                Total_NetoSinIva += NetoSinIva
                listaCuentaCorrientePorCliente[i].update({'NetoSinIva': NetoSinIva})
                i += 1


            ## Linea para acomodar los registros de manera descente
            listaCuentaCorrientePorCliente = sorted(listaCuentaCorrientePorCliente, key=lambda k: k['TotalCms'],
                                                    reverse=True)

            total_porcentajeTotalCms = 0
            total_porcentajeNetoSinIva = 0
            for data in listaCuentaCorrientePorCliente:
                porcentajeTotalCms = 0
                if Total_TotalCms != 0:
                    porcentajeTotalCms = (data['TotalCms'] / Total_TotalCms) * 100
                    total_porcentajeTotalCms += porcentajeTotalCms

                porcentajeNetoSinIva = 0
                if Total_NetoSinIva != 0:
                    porcentajeNetoSinIva = (data['NetoSinIva'] / Total_NetoSinIva) * 100
                    total_porcentajeNetoSinIva += porcentajeNetoSinIva

                if (int(data['Grupo']) == 3):
                    data['Grupo'] = 'Interior'
                elif (int(data['Grupo']) == 4):
                    data['Grupo'] = 'Capital'
                elif (int(data['Grupo']) == 5):
                    data['Grupo'] = 'Ventura'
                elif (int(data['Grupo']) == 6):
                    data['Grupo'] = 'Oficiales'
                elif (int(data['Grupo']) == 7):
                    data['Grupo'] = 'Canjes'
                elif (int(data['Grupo']) == 9):
                    data['Grupo'] = 'Directas'
                elif (int(data['Grupo']) == 10):
                    data['Grupo'] = 'Directas'
                else:
                    data['Grupo'] = 'Registro/s indefinidos y/o sin Grupo'
                data.update({'PorcentajeCms': porcentajeTotalCms, 'PorcentajeNetoSinIva': porcentajeNetoSinIva})

            listaCuentaCorrientePorCliente.append(
                {'Grupo': '', 'TotalCms': '', 'DescCms': '', 'CmsNeto': '', 'TotalBruto': '',
                 'TotalDescuento': '', 'NetoSinIva': '', 'PorcentajeCms': '', 'PorcentajeNetoSinIva': ''})

            listaCuentaCorrientePorCliente.append(
                {'Grupo': 'Total General', 'TotalCms': Total_TotalCms, 'DescCms': Total_DescCms,
                 'CmsNeto': Total_CmsNeto, 'TotalBruto': Total_TotalBruto,
                 'TotalDescuento': Total_TotalDescuento, 'NetoSinIva': Total_NetoSinIva,
                 'PorcentajeCms': total_porcentajeTotalCms, 'PorcentajeNetoSinIva': total_porcentajeNetoSinIva})

            request.session['data'] = listaCuentaCorrientePorCliente

            request.session['headers'] = ['Cliente', 'TotalCms', 'Desc Cms', 'Cms Neto', 'Total Bruto',
                                          'Total Descuento', 'Neto Sin Iva', '% Cms', '% Neto Sin Iva']

            if tit == u'Contado':
                request.session['titulo'] = 'Clientes de Contado'
            elif tit == u'Cuenta':
                request.session['titulo'] = 'Clientes de Cuenta Corriente'
            else:
                request.session['titulo'] = 'Clientes de ' + tit

            request.session['keys'] = ['Grupo', 'TotalCms', 'DescCms', 'CmsNeto', 'TotalBruto',
                                       'TotalDescuento', 'NetoSinIva', 'PorcentajeCms', 'PorcentajeNetoSinIva']

            request.session['reporteConTotales'] = len(listaCuentaCorrientePorCliente)

            listaCuentaCorrientePorCliente = json.dumps(listaCuentaCorrientePorCliente, cls=DjangoJSONEncoder)
            # pprint.pprint(listaCuentaCorrientePorCliente)
            return HttpResponse(json.dumps(
                {'agrupacion': agrupacion, 'listaCuentaCorrientePorCliente': listaCuentaCorrientePorCliente}),
                content_type='application/javascript')  # reemplazo el simplejason x json
        else:
            request.session['data'] = listaCuentaCorriente

            request.session['headers'] = ['Ag. Cliente', 'Codigo', 'Aviso', 'Total Cms', 'Desc Cms', 'Cms Neto',
                                          'V. Anuncio',
                                          'Rec. Color',
                                          'Rec. Logo', 'Desc. Manual', 'Tot. Recargo', 'Tot. Bruto', 'Desc. Promocion',
                                          'Desc. Convenio',
                                          'Com Agencia', 'Desc. Agencia', 'Total Desc.', 'Neto Sin Iva',
                                          'Fecha Factura', 'Nº Factura', 'Nº pedido', 'Codigo Aviso',
                                          'Orden Publicidad']

            request.session['keys'] = ['AgenciaCliente', 'Codigo', 'Aviso', 'TotalCms', 'DescCms', 'CmsNeto',
                                       'ValorAnuncio',
                                       'RecargoColor', 'RecargoLogo', 'DescManual', 'TotalRecargo', 'TotalBruto',
                                       'DescPromocion', 'DescConvenio', 'ComAgencia', 'DescAgencia', 'TotalDescuento',
                                       'NetoSinIva', 'fechafactura', 'nrofactura', 'nropedido', 'CodigoAviso',
                                       'OrdenPublicidad']
            request.session['agrupacion'] = 'Grupo'
            if tit == u'Contado':
                request.session['titulo'] = 'Contado'
                request.session['headers'] = ['Ag. Cliente', 'Aviso', 'Total Cms', 'Desc Cms', 'Cms Neto', 'V. Anuncio',
                                              'Rec. Color',
                                              'Rec. Logo', 'Desc. Manual', 'Tot. Recargo', 'Tot. Bruto',
                                              'Desc. Promocion',
                                              'Desc. Convenio',
                                              'Com Agencia', 'Desc. Agencia', 'Total Desc.', 'Neto Sin Iva',
                                              'Fecha Factura', 'Nº Factura', 'Nº pedido', 'Codigo Aviso']

                request.session['keys'] = ['AgenciaCliente', 'Aviso', 'TotalCms', 'DescCms', 'CmsNeto', 'ValorAnuncio',
                                           'RecargoColor', 'RecargoLogo', 'DescManual', 'TotalRecargo', 'TotalBruto',
                                           'DescPromocion', 'DescConvenio', 'ComAgencia', 'DescAgencia',
                                           'TotalDescuento',
                                           'NetoSinIva', 'fechafactura', 'nrofactura', 'nropedido', 'CodigoAviso']
            elif tit == u'Cuenta':
                request.session['titulo'] = 'Cuenta Corriente'
            else:
                request.session['titulo'] = tit
            return HttpResponse(json.dumps({'agrupacion': 'Grupo'}), content_type='application/javascript')

    request.session['agrupacion'] = 'Grupo'
    agrupacion = request.session['agrupacion']
    fechaDesde = request.session['fechaDesde']
    fechaHasta = request.session['fechaHasta']
    codigoRemoto = request.session['codigoRemoto']
    tit = request.session['titulo']
    if tit != 'Cuenta Corriente':
        tit = 'Cuenta Corriente'

    return render_to_response('reportesEstadisticos/reportesFormasPago/cuentaCorrienteA.html',
                              {'agrupacion': agrupacion, 'fechaDesde': fechaDesde, 'fechaHasta': fechaHasta,
                               'codigoRemoto': codigoRemoto, 'tit': tit}, context_instance=RequestContext(request))


def ajaxGruposCuentaCorriente(request, lista, titulo, agrupacion):
    # 1: tipo de Aviso     ---------------------  2: Tipo de cliente  -------------- 3: No resumido
    if agrupacion == u'1':

        listaOrdenada = sorted(lista, key=operator.itemgetter('Aviso'))
        listaPorAviso = []
        Total_TotalCms = 0
        Total_DescCms = 0
        Total_CmsNeto = 0
        Total_TotalBruto = 0
        Total_TotalDescuento = 0
        Total_NetoSinIva = 0
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['Aviso']):
            TotalCms = sum(item['TotalCms'] for item in val)
            Total_TotalCms += TotalCms
            # aca creo la lista por primera vez con los N tipo de avisos que existen
            listaPorAviso.append({'Aviso': key, 'TotalCms': TotalCms})

        i = 0
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['Aviso']):
            DescCms = sum(item['DescCms'] for item in val)
            Total_DescCms += DescCms
            listaPorAviso[i].update({'DescCms': DescCms})
            i += 1

        i = 0
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['Aviso']):
            CmsNeto = sum(item['CmsNeto'] for item in val)
            Total_CmsNeto += CmsNeto
            listaPorAviso[i].update({'CmsNeto': CmsNeto})
            i += 1

        i = 0
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['Aviso']):
            TotalBruto = sum(item['TotalBruto'] for item in val)
            Total_TotalBruto += TotalBruto
            listaPorAviso[i].update({'TotalBruto': TotalBruto})
            i += 1

        i = 0
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['Aviso']):
            TotalDescuento = sum(item['TotalDescuento'] for item in val)
            Total_TotalDescuento += TotalDescuento
            listaPorAviso[i].update({'TotalDescuento': TotalDescuento})
            i += 1

        i = 0
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['Aviso']):
            NetoSinIva = sum(item['NetoSinIva'] for item in val)
            Total_NetoSinIva += NetoSinIva
            listaPorAviso[i].update({'NetoSinIva': NetoSinIva})
            i += 1

        # # Se agrega esta línea para ordenar los registros de manera ascendente.
        listaPorAviso = sorted(listaPorAviso, key=lambda k: k['TotalCms'], reverse=True)

        total_porcentajeTotalCms = 0
        total_porcentajeNetoSinIva = 0
        for data in listaPorAviso:
            porcentajeTotalCms = 0
            if Total_TotalCms != 0:
                porcentajeTotalCms = (data['TotalCms'] / Total_TotalCms) * 100
                total_porcentajeTotalCms += porcentajeTotalCms

            porcentajeNetoSinIva = 0
            if Total_NetoSinIva != 0:
                porcentajeNetoSinIva = (data['NetoSinIva'] / Total_NetoSinIva) * 100
                total_porcentajeNetoSinIva += porcentajeNetoSinIva

            data.update({'PorcentajeCms': porcentajeTotalCms, 'PorcentajeNetoSinIva': porcentajeNetoSinIva})

        listaPorAviso.append({'Aviso': '', 'TotalCms': '', 'DescCms': '', 'CmsNeto': '', 'TotalBruto': '',
                              'TotalDescuento': '', 'NetoSinIva': '', 'PorcentajeCms': '', 'PorcentajeNetoSinIva': ''})

        listaPorAviso.append(
            {'Aviso': 'Total General', 'TotalCms': Total_TotalCms, 'DescCms': Total_DescCms, 'CmsNeto': Total_CmsNeto,
             'TotalBruto': Total_TotalBruto,
             'TotalDescuento': Total_TotalDescuento, 'NetoSinIva': Total_NetoSinIva,
             'PorcentajeCms': total_porcentajeTotalCms, 'PorcentajeNetoSinIva': total_porcentajeNetoSinIva})


        ##################   Cargo las variables de session necesarias para hacer el excel       #################
        request.session['data'] = listaPorAviso

        request.session['headers'] = ['Aviso', 'TotalCms', 'Desc Cms', 'Cms Neto', 'Total Bruto',
                                      'Total Descuento', 'Neto Sin Iva', '% Cms', '% Neto Sin Iva']

        request.session['titulo'] = 'Avisos de ' + titulo

        # las variables de las fechas no las cargo porque ya las cargo cuando hago la consulta
        # request.session['fechaDesde'] = 0
        # request.session['fechaHasta'] = 0

        request.session['keys'] = ['Aviso', 'TotalCms', 'DescCms', 'CmsNeto', 'TotalBruto',
                                   'TotalDescuento', 'NetoSinIva', 'PorcentajeCms', 'PorcentajeNetoSinIva']

        request.session['reporteConTotales'] = len(listaPorAviso)
        # pprint.pprint(listaInteriorPorAviso)
        listaPorAviso = json.dumps(listaPorAviso, cls=DjangoJSONEncoder)
        return listaPorAviso

    else:
        # ##### Hacemos lo mismo que arriba pero ahora ordenamos por Tipo de Cliente ##################################

        listaOrdenada = sorted(lista, key=operator.itemgetter('AgenciaCliente'))
        listaPorCliente = []
        Total_TotalCms = 0
        Total_DescCms = 0
        Total_CmsNeto = 0
        Total_TotalBruto = 0
        Total_TotalDescuento = 0
        Total_NetoSinIva = 0
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['AgenciaCliente']):
            TotalCms = sum(item['TotalCms'] for item in val)
            Total_TotalCms += TotalCms
            # aca creo la lista por primera vez con los N tipo de avisos que existen
            listaPorCliente.append({'AgenciaCliente': key, 'TotalCms': TotalCms})

        i = 0
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['AgenciaCliente']):
            DescCms = sum(item['DescCms'] for item in val)
            Total_DescCms += DescCms
            listaPorCliente[i].update({'DescCms': DescCms})
            i += 1

        i = 0
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['AgenciaCliente']):
            CmsNeto = sum(item['CmsNeto'] for item in val)
            Total_CmsNeto += CmsNeto
            listaPorCliente[i].update({'CmsNeto': CmsNeto})
            i += 1

        i = 0
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['AgenciaCliente']):
            TotalBruto = sum(item['TotalBruto'] for item in val)
            Total_TotalBruto += TotalBruto
            listaPorCliente[i].update({'TotalBruto': TotalBruto})
            i += 1

        i = 0
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['AgenciaCliente']):
            TotalDescuento = sum(item['TotalDescuento'] for item in val)
            Total_TotalDescuento += TotalDescuento
            listaPorCliente[i].update({'TotalDescuento': TotalDescuento})
            i += 1

        i = 0
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['AgenciaCliente']):
            NetoSinIva = sum(item['NetoSinIva'] for item in val)
            Total_NetoSinIva += NetoSinIva
            listaPorCliente[i].update({'NetoSinIva': NetoSinIva})
            i += 1


        ## Linea para acomodar los registros de manera descente
        listaPorCliente = sorted(listaPorCliente, key=lambda k: k['TotalCms'], reverse=True)

        total_porcentajeTotalCms = 0
        total_porcentajeNetoSinIva = 0
        for data in listaPorCliente:
            porcentajeTotalCms = 0
            if Total_TotalCms != 0:
                porcentajeTotalCms = (data['TotalCms'] / Total_TotalCms) * 100
                total_porcentajeTotalCms += porcentajeTotalCms

            porcentajeNetoSinIva = 0
            if Total_NetoSinIva != 0:
                porcentajeNetoSinIva = (data['NetoSinIva'] / Total_NetoSinIva) * 100
                total_porcentajeNetoSinIva += porcentajeNetoSinIva

            data.update({'PorcentajeCms': porcentajeTotalCms, 'PorcentajeNetoSinIva': porcentajeNetoSinIva})

        listaPorCliente.append({'AgenciaCliente': '', 'TotalCms': '', 'DescCms': '', 'CmsNeto': '', 'TotalBruto': '',
                                'TotalDescuento': '', 'NetoSinIva': '', 'PorcentajeCms': '',
                                'PorcentajeNetoSinIva': ''})

        listaPorCliente.append({'AgenciaCliente': 'Total General', 'TotalCms': Total_TotalCms, 'DescCms': Total_DescCms,
                                'CmsNeto': Total_CmsNeto, 'TotalBruto': Total_TotalBruto,
                                'TotalDescuento': Total_TotalDescuento, 'NetoSinIva': Total_NetoSinIva,
                                'PorcentajeCms': total_porcentajeTotalCms,
                                'PorcentajeNetoSinIva': total_porcentajeNetoSinIva})

        request.session['data'] = listaPorCliente

        request.session['headers'] = ['Cliente', 'TotalCms', 'Desc Cms', 'Cms Neto', 'Total Bruto',
                                      'Total Descuento', 'Neto Sin Iva', '% Cms', '% Neto Sin Iva']

        request.session['titulo'] = 'Agencias de ' + titulo

        request.session['keys'] = ['AgenciaCliente', 'TotalCms', 'DescCms', 'CmsNeto', 'TotalBruto',
                                   'TotalDescuento', 'NetoSinIva', 'PorcentajeCms', 'PorcentajeNetoSinIva']

        request.session['reporteConTotales'] = len(listaPorCliente)

        listaPorCliente = json.dumps(listaPorCliente, cls=DjangoJSONEncoder)
        return listaPorCliente


@login_required
def grupo(request):
    listaInterior = []
    listaCapital = []
    listaVentura = []
    listaOficiales = []
    listaCanjes = []
    listaDirectas = []
    listaGrupo = []
    titulo = ''
    request.session['reporteConTotales'] = 0
    listaCCA = request.session['lista_ccA']
    # pprint.pprint(request.META['PATH_INFO'])
    # pprint.pprint('1' in request.META['PATH_INFO'])
    for data in listaCCA:

        if int(data['Grupo']) == 3:
            listaInterior.append(data)
        if int(data['Grupo']) == 4:
            listaCapital.append(data)
        if int(data['Grupo']) == 5:
            listaVentura.append(data)
        if int(data['Grupo']) == 6:
            listaOficiales.append(data)
        if int(data['Grupo']) == 7:
            listaCanjes.append(data)
        if int(data['Grupo']) == 9 or int(data['Grupo']) == 10:
            listaDirectas.append(data)

    if '1' in request.META['PATH_INFO']:
        titulo = 'Interior'
        parametro = 1
        listaGrupo = listaInterior
    elif '2' in request.META['PATH_INFO']:
        titulo = 'Capital'
        parametro = 2
        listaGrupo = listaCapital
    elif '3' in request.META['PATH_INFO']:
        titulo = 'Oficiales'
        parametro = 3
        listaGrupo = listaOficiales
    elif '4' in request.META['PATH_INFO']:
        titulo = 'Ventura'
        parametro = 4
        listaGrupo = listaVentura
    elif '5' in request.META['PATH_INFO']:
        titulo = 'Directas'
        parametro = 5
        listaGrupo = listaDirectas
    elif '6' in request.META['PATH_INFO']:
        titulo = 'Canjes'
        parametro = 6
        listaGrupo = listaCanjes

    if request.method == 'POST' and request.is_ajax():
        agrupacion = request.POST["agrupacion"]
        listaSalida = ajaxGruposCuentaCorriente(request, listaGrupo, titulo, agrupacion)
        if agrupacion == u'1':
            return HttpResponse(json.dumps({'agrupacion': agrupacion, 'listaGrupoPorAviso': listaSalida}),
                                content_type='application/javascript')
        elif agrupacion == u'2':
            return HttpResponse(json.dumps({'agrupacion': agrupacion, 'listaGrupoPorCliente': listaSalida}),
                                content_type='application/javascript')
        else:
            # muy importante para eliminar la varible de sesion que muestra los totales de una lista, poniendolo a 0 digo que no quiero totalizar la lista.
            request.session['reporteConTotales'] = 0

            request.session['data'] = listaGrupo

            request.session['headers'] = ['Aviso', 'Total Cms', 'Desc Cms', 'Cms Neto', 'V. Anuncio', 'Rec. Color',
                                          'Rec. Logo',
                                          'Desc. Manual',
                                          'Tot. Recargo', 'Tot. Bruto', 'Desc. Promocion', 'Desc. Convenio',
                                          'Com Agencia',
                                          'Desc. Agencia',
                                          'Total Desc.', 'Neto Sin Iva', 'Fecha Factura', 'Nº factura', 'Nº pedido',
                                          'Codigo Aviso', 'Orden Publicidad']
            request.session['titulo'] = titulo

            request.session['keys'] = ['Aviso', 'TotalCms', 'DescCms', 'CmsNeto', 'ValorAnuncio', 'RecargoColor',
                                       'RecargoLogo',
                                       'DescManual', 'TotalRecargo', 'TotalBruto', 'DescPromocion', 'DescConvenio',
                                       'ComAgencia', 'DescAgencia', 'TotalDescuento', 'NetoSinIva', 'fechafactura',
                                       'nrofactura', 'nropedido', 'CodigoAviso', 'OrdenPublicidad']

            return HttpResponse(json.dumps({'agrupacion': agrupacion}), content_type='application/javascript')

    request.session['titulo'] = titulo  # este titulo es para el excel

    listaGrupo = sorted(listaGrupo, key=operator.itemgetter('Aviso'))
    request.session['listaCCA_Grupo'] = listaGrupo
    request.session['agrupacion'] = 'Cliente'

    fechaDesde = request.session['fechaDesde']
    fechaHasta = request.session['fechaHasta']
    codigoRemoto = request.session['codigoRemoto']
    tit = request.session['titulo']  # ESte titulo es para el html

    return render_to_response('reportesEstadisticos/reportesFormasPago/grupoCuentaCorriente.html',
                              {'fechaDesde': fechaDesde, 'fechaHasta': fechaHasta, 'parametro': parametro,
                               'codigoRemoto': codigoRemoto, 'tit': tit},
                              context_instance=RequestContext(request))


@login_required
def ventasMensuales(request):
    try:

        if request.method == 'POST':
            formulario = formTotalVentaPublicidad(request.POST)

            if formulario.is_valid():

                cursor = connections['sqlserver2008'].cursor()
                fechaDesde = formulario.cleaned_data['fechaDesde']
                df = DateFormat(fechaDesde)
                fechaDesde = df.format('Y-d-m')

                # Se hace para verificar que se guarde un mes
                request.session['dia'] = df.format('d')

                # Para poder guardar en la BD
                request.session['mesDesdeAGuardar'] = df.format('m')
                request.session['anioDesdeAGuardar'] = df.format('Y')

                fechaDesdeModoLatino = df.format('d/m/Y')

                fechaHasta = formulario.cleaned_data['fechaHasta']
                df = DateFormat(fechaHasta)
                fechaHasta = df.format('Y-d-m')

                # Para poder guardar en la BD
                request.session['mesHastaAGuardar'] = df.format('m')
                request.session['anioHastaAGuardar'] = df.format('y')

                fechaHastaModoLatino = df.format('d/m/Y')
                # formaDePago = 1 # No importa el valor, para el script SQL es indiferente.

                request.session['fechaDesde'] = fechaDesdeModoLatino
                request.session['fechaHasta'] = fechaHastaModoLatino

                codRemoto = formulario.cleaned_data['codRemoto']
                if codRemoto == u'1':
                    request.session['codigoRemoto'] = 'Chaco'
                else:
                    request.session['codigoRemoto'] = 'Corrientes'

                cursor.execute("SELECT * FROM TotalesEstadisticasPrueba2(%s, %s, %s)",
                               (fechaDesde, fechaHasta, codRemoto))

                listaBruta = []
                for data in dictfetchall(cursor):
                    dictionary = dict(Grupo=data['Grupo'], AgenciaCliente=data['AgenciaCliente'], Codigo=data['Codigo'],
                                      Aviso=data['Aviso'], centimetros=data['centimetros'],
                                      ValorAnuncio=data['ValorAnuncio'], RecargoColor=data['RecargoColor'],
                                      RecargoLogo=data['RecargoLogo'], DescPromocion=data['DescPromocion'],
                                      DescConvenio=data['DescConvenio'],
                                      DescAgencia=data['DescAgencia'], DescuentoAMano=data['DescuentoAMano'],
                                      fechafactura=data['fechafactura'],
                                      nrofactura=data['nrofactura'], nropedido=data['nropedido'],
                                      CodigoAviso=data['CodigoAviso'],
                                      OrdenPublicidad=data['OrdenPublicidad'],
                                      ValorSinImpuestos=data['ValorSinImpuestos'], CondImpuesto=data['CondImpuesto'],
                                      valorapagar=data['valorapagar'], SupSaCh=data['SupSaCh'],
                                      cms_puro=data['cms_puro'], nombre=data[
                            'nombre'])  #esta es la transformación de la lista anterior mediante formulas.
                    listaBruta.append(dictionary)

                listaTotales = []
                if listaBruta != []:
                    for elemento in listaBruta:
                        nombre = (elemento['nombre']).replace(' ',
                                                              '')  #Esto es porque se muere el JS con muchos espacios en blanco
                        if nombre != u'CuentaCorriente':
                            elemento['Grupo'] = 99
                        else:
                            if elemento['Grupo'] == None:
                                elemento['Grupo'] = 0
                            else:
                                elemento['Grupo'] = int(elemento['Grupo'])
                                if elemento['Grupo'] == 10:
                                    elemento['Grupo'] = 9

                    listaBrutaOrdenada = sorted(listaBruta, key=operator.itemgetter('Grupo'))

                    grupoAnterior = int(listaBrutaOrdenada[0]['Grupo'])
                    total_NetoSinIva = 0
                    total_centimetros = 0
                    subTotal_centimetros = 0
                    subTotal_netoSinIva = 0

                    # Inicializaciones para el gráfico de recargos y descuentos

                    recargoColorSumatoria = 0
                    recargoLogoSumatoria = 0
                    recargoManualSumatoria = 0

                    descPromocionSumatoria = 0
                    descConvenioSumatoria = 0
                    descAManoSumatoria = 0
                    descAgenciaSumatoria = 0

                    totalRecargoSumatoria = 0
                    totalDescuentoSumatoria = 0

                    listaParaGraficoPorFormaDePago = []

                    for data in listaBrutaOrdenada:
                        resultado = transformacionGenerica(data)

                        grupo = data['Grupo']

                        if grupoAnterior != grupo:
                            total_NetoSinIva = total_NetoSinIva + subTotal_netoSinIva
                            total_centimetros = total_centimetros + subTotal_centimetros

                            dictionary = dict(Grupo=grupoAnterior, TotalCms=round(subTotal_centimetros, 2),
                                              NetoSinIva=round(subTotal_netoSinIva, 2))

                            listaTotales.append(dictionary)


                            # Se setea a 0 cuando cambia el grupo.
                            subTotal_netoSinIva = 0
                            subTotal_centimetros = 0

                        subTotal_netoSinIva += resultado['netoSinIva']
                        subTotal_centimetros += resultado['cmsNeto']
                        grupoAnterior = grupo

                        # Todas estas sumatorias son para el grafico de los recargos y descuentos
                        recargoColorSumatoria = recargoColorSumatoria + data['RecargoColor']
                        recargoLogoSumatoria = recargoLogoSumatoria + data['RecargoLogo']
                        recargoManualSumatoria = recargoManualSumatoria + resultado['descManual']

                        descPromocionSumatoria = descPromocionSumatoria + data['DescPromocion']
                        descConvenioSumatoria = descConvenioSumatoria + data['DescConvenio']
                        descAManoSumatoria = descAManoSumatoria + resultado['descAMano']
                        descAgenciaSumatoria = descAgenciaSumatoria + data['DescAgencia']

                        totalRecargoSumatoria = totalRecargoSumatoria + resultado['totalRecargo']
                        totalDescuentoSumatoria = totalDescuentoSumatoria + resultado['totalDescuento']

                        #creo lista de diccionario para hacer el grafico de formas de pago
                        listaParaGraficoPorFormaDePago.append(dict(cms=resultado['cmsNeto'], aviso=data['Aviso'],
                                                                   nombre=data['nombre'].replace(' ', '').replace('_',
                                                                                                                  '')))


                    # Esto se hace de nuevo porque la última vez no acumula
                    total_NetoSinIva = total_NetoSinIva + subTotal_netoSinIva
                    total_centimetros = total_centimetros + subTotal_centimetros

                    dictionary = dict(Grupo=grupoAnterior, TotalCms=round(subTotal_centimetros, 2),
                                      NetoSinIva=round(subTotal_netoSinIva, 2))

                    dictionaryBlanco = dict(Grupo='algo', TotalCms=' ', NetoSinIva=' ')

                    dictionary2 = dict(Grupo=8000, TotalCms=round(round(total_centimetros, 2)),
                                       NetoSinIva=round(round(total_NetoSinIva, 2)))
                    # Diccionario adicional para hacer gráfico de recargos y descuentos

                    diccionarioRecyDesc = dict(RecargoColor=recargoColorSumatoria, RecargoLogo=recargoLogoSumatoria,
                                               RecargoManual=recargoManualSumatoria,
                                               DescPromocion=descPromocionSumatoria,
                                               DescConvenio=descConvenioSumatoria, DescAMano=descAManoSumatoria,
                                               DescAgencia=descAgenciaSumatoria, TotalRecargo=totalRecargoSumatoria,
                                               TotalDescuento=totalDescuentoSumatoria, TotalNetoSinIva=total_NetoSinIva)

                    #Variables de sesion para los graficos de Recargo, Descuento y de Formas de Pago.
                    request.session['diccionarioRecyDesc'] = diccionarioRecyDesc
                    request.session['listaParaGraficoPorFormaDePago'] = listaParaGraficoPorFormaDePago

                    listaTotales.append(dictionary)
                    listaTotales.append(dictionaryBlanco)
                    listaTotales.append(dictionary2)



                    # detalleCmsVendidosyCedidos(listaBrutaParaGrafico, dictionary2['NetoSinIva'])

                else:
                    listaTotales = listaBruta

                request.session['lista_resultados'] = listaTotales

                lista = []

                band99 = False
                band3 = False
                band4 = False
                band5 = False
                band6 = False
                band7 = False
                band9 = False
                for data in listaTotales:
                    i = data['Grupo']

                    if (isinstance(data['NetoSinIva'], float)):
                        # valor = round(((float(data['NetoSinIva']) * 100) / total_NetoSinIva), 2)
                        valor = (float(data['NetoSinIva']) * 100) / total_NetoSinIva
                        if i == 99:
                            lista.append(dict(nombre='Contado', valor=valor))
                            band99 = True
                        if i == 3:
                            lista.append(dict(nombre='Interior', valor=valor))
                            band3 = True
                        if i == 4:
                            lista.append(dict(nombre='Capital', valor=valor))
                            band4 = True
                        if i == 5:
                            lista.append(dict(nombre='Ventura', valor=valor))
                            band5 = True
                        if i == 6:
                            lista.append(dict(nombre='Oficial', valor=valor))
                            band6 = True
                        if i == 7:
                            lista.append(dict(nombre='Canjes', valor=valor))
                            band7 = True
                        if i == 9:
                            lista.append(dict(nombre='Directas', valor=valor))
                            band9 = True

                if not band99:
                    lista.append(dict(nombre='Contado', valor=0))
                if not band3:
                    lista.append(dict(nombre='Interior', valor=0))
                if not band4:
                    lista.append(dict(nombre='Capital', valor=0))
                if not band5:
                    lista.append(dict(nombre='Ventura', valor=0))
                if not band6:
                    lista.append(dict(nombre='Oficial', valor=0))
                if not band7:
                    lista.append(dict(nombre='Canjes', valor=0))
                if not band9:
                    lista.append(dict(nombre='Directas', valor=0))

                request.session['lista_totales'] = listaTotales
                request.session['agrupacion'] = 'Totales'  #Se ocupa después para poder discriminar en el PDF

                # Lo pongo en Blanco porque no siempre lo voy a ocupar, es el mensaje de si se pudo guardar en la bd el registro de ventas anuales
                request.session['mensaje'] = ''

                lista = json.dumps(lista, cls=DjangoJSONEncoder)
                request.session['listaParaGrafico'] = lista

                fechaDesde = request.session['fechaDesde']
                fechaHasta = request.session['fechaHasta']
                codigoRemoto = request.session['codigoRemoto']

                tit = 'Informes Totales'

                request.session['puedeGuardarMes'] = True

                mes = request.session['mesDesdeAGuardar']
                anio = request.session['anioDesdeAGuardar']
                id = obtenerIdRegVentasNetasAnuales(mes, anio, codigoRemoto)

                request.session['idLineaPublicidad'] = id

                if request.session['detalleRecargosyDescuentos'] == 1:
                    return HttpResponseRedirect('/detalleRecargosyDescuentos/')

                return render_to_response('reportesEstadisticos/ventasMensuales/ventaMensual.html',
                                          {'listaParaGrafico': lista, 'fechaDesde': fechaDesde,
                                           'fechaHasta': fechaHasta,
                                           'codigoRemoto': codigoRemoto, 'tit': tit, 'id': id},
                                          context_instance=RequestContext(request))

        else:

            if request.session['listaParaGrafico'] != 0 and request.session['titulo'] == 'Totales Publicidad':
                # if 1 == 2:
                lista = request.session['listaParaGrafico']
                fechaDesde = request.session['fechaDesde']
                fechaHasta = request.session['fechaHasta']
                codigoRemoto = request.session['codigoRemoto']
                tit = 'Informes Totales'
                id = request.session['idLineaPublicidad']

                return render_to_response('reportesEstadisticos/ventasMensuales/ventaMensual.html',
                                          {'listaParaGrafico': lista, 'fechaDesde': fechaDesde,
                                           'fechaHasta': fechaHasta,
                                           'codigoRemoto': codigoRemoto, 'tit': tit, 'id': id},
                                          context_instance=RequestContext(request))
            else:
                request.session['listaParaGrafico'] = 0
                formulario = formTotalVentaPublicidad()

        return render_to_response('reportesEstadisticos/ventasMensuales/formVentaMensual.html',
                                  {'formulario': formulario},
                                  context_instance=RequestContext(request))
    except Exception as e:

        return HttpResponseRedirect('/errorGeneral', {'mensaje': e.message,
                                                      'tipo': type(e)})  # , context_instance=RequestContext(request)


def cargarVentasTotales(request, codigoRemoto):
    cursor = connections['default'].cursor()

    cursor.execute("select mes,anio ,directas_cms,directas_neto_sin_iva,capital_cms,capital_neto_sin_iva,"
                   "interior_cms,interior_neto_sin_iva, ventura_cms ,ventura_neto_sin_iva, oficiales_cms,"
                   "oficiales_neto_sin_iva, canjes_cms ,canjes_neto_sin_iva, contado_cms, "
                   "contado_neto_sin_iva , total_cms,total_neto_sin_iva, codigo_remoto, activo "
                   " from lineaventapublicidad WHERE activo = 1 and codigo_remoto = %s order by anio, mes",
                   [codigoRemoto])

    listaTotal = dictfetchall(cursor)

    # Agregado para el gráfico lineal
    listaParaGrafico = []
    for data in listaTotal:
        listaParaGrafico.append(dict(mes=data['mes'], anio=data['anio'], TotalCms=data['total_cms']))

    # request.session['listaParaGrafico'] = listaParaGrafico
    request.session['listaParaGraficoJson'] = json.dumps(listaParaGrafico, cls=DjangoJSONEncoder)

    for data in listaTotal:
        mes = data['mes']
        if mes == 1:
            data['mes'] = 'Enero'
        elif mes == 2:
            data['mes'] = 'Febrero'
        elif mes == 3:
            data['mes'] = 'Marzo'
        elif mes == 4:
            data['mes'] = 'Abril'
        elif mes == 5:
            data['mes'] = 'Mayo'
        elif mes == 6:
            data['mes'] = 'Junio'
        elif mes == 7:
            data['mes'] = 'Julio'
        elif mes == 8:
            data['mes'] = 'Agosto'
        elif mes == 9:
            data['mes'] = 'Septiembre'
        elif mes == 10:
            data['mes'] = 'Octubre'
        elif mes == 11:
            data['mes'] = 'Noviembre'
        else:
            data['mes'] = 'Diciembre'

    request.session['agrupacion'] = 'VentaNetaAnual'

    request.session['lista_resultados'] = listaTotal


def formVentasNetasAnuales(request):
    if request.method == 'POST':
        formulario = formVentaNetaAnual(request.POST)
        if formulario.is_valid():
            codRemoto = formulario.cleaned_data['codRemoto']
            if codRemoto == u'1':
                request.session['codigoRemoto'] = 'Chaco'
            else:
                request.session['codigoRemoto'] = 'Corrientes'
            codigoRemoto = request.session['codigoRemoto']
            cargarVentasTotales(request, codigoRemoto)
            listaParaGraficoJson = request.session['listaParaGraficoJson']
            return render_to_response('reportesEstadisticos/ventaNetaAnual/ventaNetaAnual.html',
                                      {'provincia': codigoRemoto, 'listaParaGrafico': listaParaGraficoJson},
                                      context_instance=RequestContext(request))
    else:
        formulario = formVentaNetaAnual()

    return render_to_response('reportesEstadisticos/ventaNetaAnual/formVentaNetaAnual.html', {'formulario': formulario},
                              context_instance=RequestContext(request))


def guardarTotales(request):
    if request.session['puedeGuardarMes']:

        fechaDesde = request.session['fechaDesde']

        fechaDesde = datetime.date(int(fechaDesde[6:10]), int(fechaDesde[3:5]), int(fechaDesde[0:2]))

        fechaHasta = request.session['fechaHasta']

        fechaHasta = datetime.date(int(fechaHasta[6:10]), int(fechaHasta[3:5]), int(fechaHasta[0:2]))
        fechaHasta = fechaHasta + datetime.timedelta(days=1)

        dif = rdelta.relativedelta(fechaHasta, fechaDesde)

        if dif.months == 1 and dif.days == 0 and int(request.session['dia']) == 1:

            # if dif.months == 1 and dif.days==0:

            listaauxiliar = request.session['lista_totales']
            directas_cms = 0
            directas_netoSinIva = 0
            capital_cms = 0
            capital_netoSinIva = 0
            interior_cms = 0
            interior_netoSinIva = 0
            oficiales_cms = 0
            oficiales_netoSinIva = 0
            canjes_cms = 0
            canjes_netoSinIva = 0
            ventura_cms = 0
            ventura_netoSinIva = 0
            contado_cms = 0
            contado_netoSinIva = 0
            total_cms = 0
            total_netoSinIva = 0

            for elemento in listaauxiliar:
                if elemento['Grupo'] == 99:
                    contado_cms = elemento['TotalCms']
                    contado_netoSinIva = elemento['NetoSinIva']
                if elemento['Grupo'] == 3:
                    interior_cms = elemento['TotalCms']
                    interior_netoSinIva = elemento['NetoSinIva']
                if elemento['Grupo'] == 4:
                    capital_cms = elemento['TotalCms']
                    capital_netoSinIva = elemento['NetoSinIva']
                if elemento['Grupo'] == 5:
                    ventura_cms = elemento['TotalCms']
                    ventura_netoSinIva = elemento['NetoSinIva']
                if elemento['Grupo'] == 6:
                    oficiales_cms = elemento['TotalCms']
                    oficiales_netoSinIva = elemento['NetoSinIva']
                if elemento['Grupo'] == 7:
                    canjes_cms = elemento['TotalCms']
                    canjes_netoSinIva = elemento['NetoSinIva']
                if elemento['Grupo'] == 9:
                    directas_cms = elemento['TotalCms']
                    directas_netoSinIva = elemento['NetoSinIva']
                if elemento['Grupo'] == 8000:
                    total_cms = elemento['TotalCms']
                    total_netoSinIva = elemento['NetoSinIva']

            # fechaGuardado = datetime.date.now().strftime('%d-%m-%Y')  #.strftime('%m-%d-%Y-%H-%M')

            try:
                cursor = connections['default'].cursor()
                # 1 ESTA ACTIVO - 0 NO ACTIVO (BAJA LOGICA)
                cursor.execute("INSERT INTO lineaventapublicidad"
                               " (mes,anio ,directas_cms,directas_neto_sin_iva ,"
                               "capital_cms,capital_neto_sin_iva ,"
                               "interior_cms,interior_neto_sin_iva ,"
                               "ventura_cms ,ventura_neto_sin_iva,"
                               "oficiales_cms,oficiales_neto_sin_iva,"
                               "canjes_cms ,canjes_neto_sin_iva, "
                               "contado_cms, contado_neto_sin_iva ,"
                               "total_cms,total_neto_sin_iva,"
                               "usuario ,codigo_remoto , fechaGuardado, activo )  "
                               "VALUES (%s,%s,%s,%s,%s ,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,GETDATE(),1)",

                               (request.session['mesDesdeAGuardar'], request.session['anioDesdeAGuardar'], directas_cms,
                                directas_netoSinIva, capital_cms, capital_netoSinIva, interior_cms, interior_netoSinIva,
                                ventura_cms, ventura_netoSinIva,
                                oficiales_cms, oficiales_netoSinIva, canjes_cms, canjes_netoSinIva, contado_cms,
                                contado_netoSinIva,
                                total_cms, total_netoSinIva, request.session['userID'],
                                request.session['codigoRemoto']
                                ))
                if request.session['idLineaPublicidad'] != 0:
                    id = request.session['idLineaPublicidad']
                    cursor.execute("UPDATE lineaventapublicidad SET activo = 0 WHERE id=%s", [id])

                request.session['puedeGuardarMes'] = False
                mensaje = 'El Informe se ha guardado correctamente'

            except DatabaseError as e:
                mensaje = e.message

            request.session['mensaje'] = mensaje
            codigoRemoto = request.session['codigoRemoto']
            cargarVentasTotales(request, codigoRemoto)
            request.session['agrupacion'] = 'VentaNetaAnual'  # Para poder discriminarlo en el view_in_pdf
            listaParaGraficoJson = request.session['listaParaGraficoJson']  # Para hacer el grafico
            return render_to_response('reportesEstadisticos/ventaNetaAnual/ventaNetaAnual.html',
                                      {'mensaje': mensaje, 'provincia': codigoRemoto,
                                       'listaParaGrafico': listaParaGraficoJson},
                                      context_instance=RequestContext(request))
    # else:
    request.session['agrupacion'] = 'VentaNetaAnual'  # Para poder discriminarlo en el view_in_pdf

    return render_to_response('reportesEstadisticos/ventaNetaAnual/ventaNetaAnual.html',
                              context_instance=RequestContext(request))


def obtenerIdRegVentasNetasAnuales(mes, anio, codigoRemoto):
    cursor2 = connections['default'].cursor()
    cursor2.execute(
        "select id from lineaventapublicidad where mes = %s and anio = %s and codigo_remoto=%s and activo = 1",
        (mes, anio, codigoRemoto))
    result = dictfetchall(cursor2)
    if not result:
        id = 0
    else:
        id = result[0]['id']

    return id


def enviarCorreoAjax(request):
    if request.method == 'POST' and request.is_ajax():  # request.POST.has_key('client_response'):

        asunto = request.POST["asunto"]
        destinatario0 = request.POST["destinatario0"]
        mailText = request.POST["mailText"]

        mailText = mailText + '\n\n\n\n ---------------------------------------- \n Fuente: Sistema de Reportes de Pasantes (SiRePa) - Enviado por usuario: ' + \
                   request.session['nombreUsuario']
        tituloDelArchivoAdjunto = ''
        listaDestinatarios = []
        for i in xrange(1, 10):
            dest = 'destinatario' + str(i)
            if request.POST[dest] != '':
                listaDestinatarios.append(request.POST[dest])

        if (request.session['agrupacion'] == 'Totales'):  # Si se agrupa por totales quiere decir que es otro informe.
            template_name = "reportesEstadisticos/ventasMensuales/ventaMensualPDF.html"  # la sesión de agrupación se setea en totales.
            tituloDelArchivoAdjunto = 'Resumen Ventas Mensuales de ' + request.session['codigoRemoto']
            request.session[
                'titulo'] = ''  # Porque no se le puede enviar variables NuLL a pdf se setean de nuevo estos valores
            lista = request.session['lista_totales']

        elif request.session['agrupacion'] == 'Cliente':
            lista = request.session['listaCCA_Grupo']
            template_name = "reportesEstadisticos/reportesFormasPago/formasDePagoPDF.html"

        elif request.session['agrupacion'] == 'VentaNetaAnual':  # Informa de ventas anuales de publicidad
            tituloDelArchivoAdjunto = 'Resumen Ventas Anuales de ' + request.session['codigoRemoto']
            lista = request.session['lista_resultados']
            anioanterior = lista[0]['anio']

            subtotal_directas_cms = 0
            subtotal_directas_neto_sin_iva = 0
            subtotal_capital_cms = 0
            subtotal_capital_neto_sin_iva = 0
            subtotal_interior_cms = 0
            subtotal_interior_neto_sin_iva = 0
            subtotal_ventura_cms = 0
            subtotal_ventura_neto_sin_iva = 0
            subtotal_oficiales_cms = 0
            subtotal_oficiales_neto_sin_iva = 0
            subtotal_canjes_cms = 0
            subtotal_canjes_neto_sin_iva = 0
            subtotal_contado_cms = 0
            subtotal_contado_neto_sin_iva = 0
            subtotal_total_cms = 0
            subtotal_total_neto_sin_iva = 0

            listaNueva = []
            for elemento in lista:

                if elemento['anio'] != anioanterior:
                    listaNueva.append(dict(anio='', mes='', directas_cms=subtotal_directas_cms,
                                           directas_neto_sin_iva=subtotal_directas_neto_sin_iva,
                                           capital_cms=subtotal_capital_cms,
                                           capital_neto_sin_iva=subtotal_capital_neto_sin_iva,
                                           interior_cms=subtotal_interior_cms,
                                           interior_neto_sin_iva=subtotal_interior_neto_sin_iva,
                                           ventura_cms=subtotal_ventura_cms,
                                           ventura_neto_sin_iva=subtotal_ventura_neto_sin_iva,
                                           oficiales_cms=subtotal_oficiales_cms,
                                           oficiales_neto_sin_iva=subtotal_oficiales_neto_sin_iva,
                                           canjes_cms=subtotal_canjes_cms,
                                           canjes_neto_sin_iva=subtotal_canjes_neto_sin_iva,
                                           contado_cms=subtotal_contado_cms,
                                           contado_neto_sin_iva=subtotal_contado_neto_sin_iva,
                                           total_cms=subtotal_total_cms,
                                           total_neto_sin_iva=subtotal_total_neto_sin_iva))

                    listaNueva.append(dict(anio='-', mes='-', directas_cms=0, directas_neto_sin_iva=0,
                                           capital_cms=0, capital_neto_sin_iva=0,
                                           interior_cms=0, interior_neto_sin_iva=0,
                                           ventura_cms=0, ventura_neto_sin_iva=0,
                                           oficiales_cms=0, oficiales_neto_sin_iva=0,
                                           canjes_cms=0, canjes_neto_sin_iva=0,
                                           contado_cms=0, contado_neto_sin_iva=0,
                                           total_cms=0, total_neto_sin_iva=0))
                    listaNueva.append(elemento)
                else:
                    listaNueva.append(elemento)

                subtotal_directas_cms = subtotal_directas_cms + elemento['directas_cms']
                subtotal_directas_neto_sin_iva = subtotal_directas_neto_sin_iva + elemento['directas_neto_sin_iva']
                subtotal_capital_cms = subtotal_capital_cms + elemento['capital_cms']
                subtotal_capital_neto_sin_iva = subtotal_capital_neto_sin_iva + elemento['capital_neto_sin_iva']
                subtotal_interior_cms = subtotal_interior_cms + elemento['interior_cms']
                subtotal_interior_neto_sin_iva = subtotal_interior_neto_sin_iva + elemento['interior_neto_sin_iva']
                subtotal_ventura_cms = subtotal_ventura_cms + elemento['ventura_cms']
                subtotal_ventura_neto_sin_iva = subtotal_ventura_neto_sin_iva + elemento['ventura_neto_sin_iva']
                subtotal_oficiales_cms = subtotal_oficiales_cms + elemento['oficiales_cms']
                subtotal_oficiales_neto_sin_iva = subtotal_oficiales_neto_sin_iva + elemento['oficiales_neto_sin_iva']
                subtotal_canjes_cms = subtotal_canjes_cms + elemento['canjes_cms']
                subtotal_canjes_neto_sin_iva = subtotal_canjes_neto_sin_iva + elemento['canjes_neto_sin_iva']
                subtotal_contado_cms = subtotal_contado_cms + elemento['contado_cms']
                subtotal_contado_neto_sin_iva = subtotal_contado_neto_sin_iva + elemento['contado_neto_sin_iva']
                subtotal_total_cms = subtotal_total_cms + elemento['total_cms']
                subtotal_total_neto_sin_iva = subtotal_total_neto_sin_iva + elemento['total_neto_sin_iva']

                anioanterior = elemento['anio']

            lista = listaNueva
            request.session['titulo'] = ''
            request.session['fechaDesde'] = ''
            request.session['fechaHasta'] = ''
            # request.session['codigoRemoto'] = ''
            template_name = "reportesEstadisticos/ventaNetaAnual/ventaNetaAnualPDF.html"
            # Las fechas y el codigo remoto no se ocupan aún en este pdf.

        else:
            lista = request.session['lista_ccA']
            template_name = "reportesEstadisticos/reportesFormasPago/formasDePagoPDF.html"

        context_dict = {

            'object_lists': lista,  # Aqui es donde llamo a las variables de sesion
            'nombreUsuario': request.session['nombreUsuario'],
            'agrupacion': request.session['agrupacion'],
            'titulo': request.session['titulo'],
            'fechaDesde': request.session['fechaDesde'],
            'fechaHasta': request.session['fechaHasta'],
            'provincia': request.session['codigoRemoto']
        }
        context_dict.update({'pagesize': 'A4'})

        template = get_template(template_name)
        context = Context(context_dict)
        html = template.render(context)
        result = StringIO.StringIO()

        links = lambda uri, rel: os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ''))
        pisa.CreatePDF(html.encode("UTF-8"), result, encoding='UTF-8', link_callback=links)

        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=' + tituloDelArchivoAdjunto + '.pdf'
        # return response

        if destinatario0 != '':
            email = EmailMessage(asunto, mailText, to=[destinatario0], )
            email.attach(tituloDelArchivoAdjunto + '.pdf', result.getvalue(), 'application/pdf')
            email.send()

        for destinatario in listaDestinatarios:
            email = EmailMessage(asunto, mailText, to=[destinatario])
            email.attach(tituloDelArchivoAdjunto + '.pdf', result.getvalue(), 'application/pdf')
            email.send()

        return HttpResponse(json.dumps({'asunto': asunto, 'destinatario': destinatario0, 'mailText': mailText}),
                            content_type='application/javascript')  # reemplazo el simplejason x json

    return render_to_response('reportesEstadisticos/ventaNetaAnual/ventaNetaAnual.html',
                              context_instance=RequestContext(request))


def detalleCmsVendidosyCedidos(request):
    if request.session['listaParaGraficoPorFormaDePago'] != 0:
        listaBruta = request.session['listaParaGraficoPorFormaDePago']

        listaBrutaOrdenada = sorted(listaBruta, key=operator.itemgetter('aviso'))

        # keys de listaParaGraficoPorFormaDePago : cms=data['cms_puro'], aviso=data['Aviso'],nombre=data['nombre'])

        listaCuentaCorriente = []
        listaContado = []
        listaCompensacion = []
        listaReposicion = []
        listaCortesia = []
        otrasFormasDePago = []
        totalCms = 0

        for data in listaBrutaOrdenada:
            totalCms += data["cms"]

            if data['nombre'] == u'CuentaCorriente':
                listaCuentaCorriente.append(dict(cms=data['cms'], aviso=data['aviso']))
            elif data['nombre'] == u'Efectivo':
                listaContado.append(dict(cms=data['cms'], aviso=data['aviso']))
            elif 'Reposici' in data['nombre']:
                listaReposicion.append(dict(cms=data['cms'], aviso=data['aviso']))
            elif data['nombre'] == u'Compensacion':
                listaCompensacion.append(dict(cms=data['cms'], aviso=data['aviso']))
            elif data['nombre'] == u'Cortesias':
                listaCortesia.append(dict(cms=data['cms'], aviso=data['aviso']))
            else:
                otrasFormasDePago.append(dict(cms=data['cms'], aviso=data['aviso']))

        listaTotalCmsOrdenadaPorAvisosYFormasDePago = []
        resumenCuentaCorriente = []
        totalCmsCuentaCorriente = 0
        # itertool.groupby recibe el paramatero lambda que es una funcion anónima que indica la clave de agropamiento; separa los diccionarios con clave
        # igual y a traves de la fucnión sum, suma los valores agrupados por clave.
        for key, val in itertools.groupby(listaCuentaCorriente, lambda v: v['aviso']):
            cms = sum(item['cms'] for item in val)
            totalCmsCuentaCorriente += cms
            resumenCuentaCorriente.append({'cms': cms, 'aviso': key})

        resumenContado = []
        totalCmsContado = 0
        for key, val in itertools.groupby(listaContado, lambda v: v['aviso']):
            cms = sum(item['cms'] for item in val)
            totalCmsContado += cms
            resumenContado.append({'cms': cms, 'aviso': key})

        resumenCompensacion = []
        totalCmsCompensacion = 0
        for key, val in itertools.groupby(listaCompensacion, lambda v: v['aviso']):
            cms = sum(item['cms'] for item in val)
            totalCmsCompensacion += cms
            resumenCompensacion.append({'cms': cms, 'aviso': key})

        resumenReposicion = []
        totalCmsReposicion = 0
        for key, val in itertools.groupby(listaReposicion, lambda v: v['aviso']):
            cms = sum(item['cms'] for item in val)
            totalCmsReposicion += cms
            resumenReposicion.append({'cms': cms, 'aviso': key})

        resumenCortesia = []
        totalCmsCortesia = 0
        for key, val in itertools.groupby(listaCortesia, lambda v: v['aviso']):
            cms = sum(item['cms'] for item in val)
            totalCmsCortesia += cms
            resumenCortesia.append({'cms': cms, 'aviso': key})

        resumenOtrasFormasDePago = []
        totalCmsOtrasFormasDePago = 0
        for key, val in itertools.groupby(otrasFormasDePago, lambda v: v['aviso']):
            cms = sum(item['cms'] for item in val)
            totalCmsOtrasFormasDePago += cms
            resumenOtrasFormasDePago.append({'cms': cms, 'aviso': key})



        # bueno hasta tengo para el primer grafico de torta
        listaTotalCmsPorFormasDePago = []

        porcCmsCuentaCorriente = (totalCmsCuentaCorriente * 100) / totalCms
        listaTotalCmsPorFormasDePago.append(dict(nombre='CuentaCorriente', porcCms=porcCmsCuentaCorriente))

        porcCmsContado = (totalCmsContado * 100) / totalCms
        listaTotalCmsPorFormasDePago.append(dict(nombre='Contado', porcCms=porcCmsContado))

        porcCmsReposicion = (totalCmsReposicion * 100) / totalCms
        listaTotalCmsPorFormasDePago.append(dict(nombre='Reposicion', porcCms=porcCmsReposicion))

        porcCmsCompensacion = (totalCmsCompensacion * 100) / totalCms
        listaTotalCmsPorFormasDePago.append(dict(nombre='Compensacion', porcCms=porcCmsCompensacion))

        porcCmsCortesia = (totalCmsCortesia * 100) / totalCms
        listaTotalCmsPorFormasDePago.append(dict(nombre='Cortesias', porcCms=porcCmsCortesia))

        porcCmsOtrasFormasDePago = (totalCmsOtrasFormasDePago * 100) / totalCms
        listaTotalCmsPorFormasDePago.append(dict(nombre='OtrasFormasDePago', porcCms=porcCmsOtrasFormasDePago))

        listaBrutaOrdenada = sorted(listaBruta, key=operator.itemgetter('nombre'))
        listaCmsParaGrid = []
        for key, val in itertools.groupby(listaBrutaOrdenada, lambda v: v['nombre']):
            cms = sum(item['cms'] for item in val)

            listaCmsParaGrid.append({'cms': cms, 'nombre': key})

        listaCmsParaGrid.append(dict(nombre='', cms=0))
        listaCmsParaGrid.append(dict(nombre='Total de Centimetros', cms=totalCms))

        listaCmsXCuentaCorriente = []
        for data in resumenCuentaCorriente:
            p = (data['cms'] * 100) / totalCmsCuentaCorriente
            listaCmsXCuentaCorriente.append(dict(aviso=data['aviso'], porcentaje=p))

        listaCmsXContado = []
        for data in resumenContado:
            p = (data['cms'] * 100) / totalCmsContado
            listaCmsXContado.append(dict(aviso=data['aviso'], porcentaje=p))

        listaCmsXCompensacion = []
        for data in resumenCompensacion:
            p = (data['cms'] * 100) / totalCmsCompensacion
            listaCmsXCompensacion.append(dict(aviso=data['aviso'], porcentaje=p))

        listaCmsXReposicion = []
        for data in resumenReposicion:
            p = (data['cms'] * 100) / totalCmsReposicion
            listaCmsXReposicion.append(dict(aviso=data['aviso'], porcentaje=p))

        listaCmsXCortesias = []
        for data in resumenCortesia:
            p = (data['cms'] * 100) / totalCmsCortesia
            listaCmsXCortesias.append(dict(aviso=data['aviso'], porcentaje=p))

        listaCmsXOtrasFormasDePago = []
        for data in resumenOtrasFormasDePago:
            p = (data['cms'] * 100) / totalCmsOtrasFormasDePago
            listaCmsXOtrasFormasDePago.append(dict(aviso=data['aviso'], porcentaje=p))

        request.session['listaParaGraficosPorFormasDePago'] = listaCmsParaGrid
        fechaDesde = request.session['fechaDesde']
        fechaHasta = request.session['fechaHasta']
        codigoRemoto = request.session['codigoRemoto']

        listaTotalCmsPorFormasDePago = json.dumps(listaTotalCmsPorFormasDePago, cls=DjangoJSONEncoder)
        listaCmsXContado = json.dumps(listaCmsXContado, cls=DjangoJSONEncoder)
        listaCmsXCompensacion = json.dumps(listaCmsXCompensacion, cls=DjangoJSONEncoder)
        listaCmsXReposicion = json.dumps(listaCmsXReposicion, cls=DjangoJSONEncoder)
        listaCmsXCortesias = json.dumps(listaCmsXCortesias, cls=DjangoJSONEncoder)
        listaCmsXOtrasFormasDePago = json.dumps(listaCmsXOtrasFormasDePago, cls=DjangoJSONEncoder)
        listaCmsXCuentaCorriente = json.dumps(listaCmsXCuentaCorriente, cls=DjangoJSONEncoder)

        return render_to_response('reportesEstadisticos/ventasMensuales/detalleCmsVendidosyCedidos.html',
                                  {'listaParaGrafico': listaTotalCmsPorFormasDePago,
                                   'listaCmsXContado': listaCmsXContado,
                                   'listaCmsXCompensacion': listaCmsXCompensacion,
                                   'listaCmsXReposicion': listaCmsXReposicion,
                                   'listaCmsXCortesias': listaCmsXCortesias,
                                   'listaCmsXOtrasFormasDePago': listaCmsXOtrasFormasDePago,
                                   'listaCmsXCuentaCorriente': listaCmsXCuentaCorriente,
                                   'fechaDesde': fechaDesde, 'fechaHasta': fechaHasta,
                                   'codigoRemoto': codigoRemoto,
                                   'tit': 'Informe de Centimetros por Formas de Pago'},
                                  context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect('/ventasMensuales')


def detalleRecargosyDescuentos(request):
    if request.session['diccionarioRecyDesc'] != 0:

        data = request.session['diccionarioRecyDesc']

        # porcentajeRecargo = round(((data['TotalRecargo'] / data['TotalNetoSinIva'])*100),2)
        # porcentajeDescuento = round(((data['TotalDescuento'] / data['TotalNetoSinIva'])*100),2)

        porcentajeRecargoLogo = round(((data['RecargoLogo'] / data['TotalRecargo']) * 100), 2)
        porcentajeRecargoColor = round(((data['RecargoColor'] / data['TotalRecargo']) * 100), 2)
        porcentajeRecargoManual = round(((data['RecargoManual'] / data['TotalRecargo']) * 100), 2)

        porcentajeDescuentoPromocion = round(((data['DescPromocion'] / data['TotalDescuento']) * 100), 2)
        porcentajeDescuentoConvenio = round(((data['DescConvenio'] / data['TotalDescuento']) * 100), 2)
        porcentajeDescuentoAMano = round(((data['DescAMano'] / data['TotalDescuento']) * 100), 2)
        porcentajeDescuentoAgencia = round(((data['DescAgencia'] / data['TotalDescuento']) * 100), 2)

        valor_anuncio = data['TotalNetoSinIva'] - data['TotalDescuento'] + data['TotalRecargo']

        lista_grid = [dict(nombre='Valor Anuncio', valor=valor_anuncio),
                      dict(nombre='Recargo Total', valor=data['TotalRecargo']),
                      dict(nombre='Descuento Total', valor=data['TotalDescuento']),
                      dict(nombre='Valor Neto sin Iva', valor=data['TotalNetoSinIva'])]

        lista_graficoRecargo = [dict(nombre='RecargoLogo', valor=porcentajeRecargoLogo),
                                dict(nombre='RecargoColor', valor=porcentajeRecargoColor),
                                dict(nombre='RecargoaMano', valor=porcentajeRecargoManual)]

        lista_graficoDescuento = [dict(nombre='DescuentoPromocion', valor=porcentajeDescuentoPromocion),
                                  dict(nombre='DescuentoConvenio', valor=porcentajeDescuentoConvenio),
                                  dict(nombre='DescuentoaMano', valor=porcentajeDescuentoAMano),
                                  dict(nombre='DescuentoAgencia', valor=porcentajeDescuentoAgencia)]

        request.session['lista_grafico_recydesc'] = lista_grid
        fechaDesde = request.session['fechaDesde']
        fechaHasta = request.session['fechaHasta']
        codigoRemoto = request.session['codigoRemoto']

        lista_grafico1 = json.dumps(lista_graficoRecargo, cls=DjangoJSONEncoder)
        lista_grafico2 = json.dumps(lista_graficoDescuento, cls=DjangoJSONEncoder)

        return render_to_response('reportesEstadisticos/ventasMensuales/detallesRecargosyDescuentos.html',
                                  {'listaParaGrafico': lista_grafico1, 'listaParaGrafico2': lista_grafico2,
                                   'fechaDesde': fechaDesde, 'fechaHasta': fechaHasta,
                                   'codigoRemoto': codigoRemoto,
                                   'tit': 'Detalle de Recargos y Descuentos'},
                                  context_instance=RequestContext(request))
    else:
        # creo esta variable para saber si selecciono desde el menú y no se puede acceder xq no estan cargadas. Una vez que se cargue el form se lo direccione directamente.
        request.session['detalleRecargosyDescuentos'] = 1
        return HttpResponseRedirect('/ventasMensuales')


# ################################### Comienzo del Indicador Resportes de Promociones ########################################################
def viewFormPromociones(request):
    # try:
    if request.method == 'POST':
        formulario = formPromociones(request.POST)
        if formulario.is_valid():
            cursor = connections['default'].cursor()

            fechaDesde = formulario.cleaned_data['fechaDesde']
            df = DateFormat(fechaDesde)
            fechaDesde = df.format('Y-d-m')

            fechaDesdeModoLatino = df.format('d/m/Y')

            fechaHasta = formulario.cleaned_data['fechaHasta']
            df = DateFormat(fechaHasta)
            fechaHasta = df.format('Y-d-m')
            fechaHastaModoLatino = df.format('d/m/Y')

            request.session['fechaDesde'] = fechaDesdeModoLatino
            request.session['fechaHasta'] = fechaHastaModoLatino

            codRemoto = formulario.cleaned_data['codRemoto']

            if codRemoto == u'1':
                request.session['codigoRemoto'] = 'Chaco'
            else:
                request.session['codigoRemoto'] = 'Corrientes'

            cursor.execute(
                "SELECT * FROM promociones where primerafechaapublicar >= %s and ultimafechaapublicar <= %s and codigoremoto = %s order by valorauxiliar",
                [fechaDesde, fechaHasta, codRemoto])

            listaAux = dictfetchall(cursor)

            request.session['lista_resultados'] = listaAux

            lista = []

            for data in (listaAux):
                data['cms_puro'] = None
                resultado = transformacionGenerica(data)
                if (data['fechafactura'] != None):
                    fechafactura = data['fechafactura'].strftime('%d/%m/%Y')
                else:
                    fechafactura = ''

                dictionary = dict(AgenciaCliente=data['AgenciaCliente'],
                                  Aviso=data['Aviso'], centimetros=data['centimetros'], DescCms=resultado['descCms'],
                                  CmsNeto=resultado['cmsNeto'],
                                  ValorAnuncio=resultado['valorAnuncio'], RecargoColor=data['RecargoColor'],
                                  RecargoLogo=data['RecargoLogo'],
                                  fechafactura=fechafactura,
                                  nrofactura=data['nrofactura'], nropedido=data['nropedido'],
                                  CodigoAviso=data['CodigoAviso'], OrdenPublicidad=data['OrdenPublicidad'],
                                  DescManual=resultado['descManual'], TotalRecargo=resultado['totalRecargo'],
                                  TotalBruto=resultado['totalBruto'],
                                  DescPromocion=data['DescPromocion'], DescConvenio=data['DescConvenio'],
                                  ComAgencia=data['DescAgencia'],
                                  DescAgencia=resultado['descAMano'], TotalDescuento=resultado['totalDescuento'],
                                  NetoSinIva=resultado['netoSinIva'],
                                  ValorAuxiliar=data['ValorAuxiliar'])
                lista.append(dictionary)

            request.session['listaPromociones'] = lista

            return render_to_response('reportesDePromociones/listaPromociones.html',
                                      context_instance=RequestContext(request))
    else:
        formulario = formPromociones()
    return render_to_response('reportesDePromociones/formPromociones.html', {'formulario': formulario},
                              context_instance=RequestContext(request))
    # except Exception as e:
    #
    # return HttpResponseRedirect('/errorGeneral', {'mensaje': e.message,
    #                                                   'tipo': type(e)})  # , context_instance=RequestContext(request)


def promociones(request):
    if request.session['listaPromociones'] != 0:
        lista2x1 = []
        lista3x1 = []
        lista3x1_2x2 = []
        lista4omas = []
        lista5x1 = []
        lista7x3 = []
        listaAg3x1 = []
        listaPromoAgCliente = []
        listaCamAuto = []
        listaCamInmobiliaria = []
        listaSinProm = []
        listaConvenios = []

        titulo = ''

        # esta variable es para el excel, para resaltar los totalizadores.
        request.session['reporteConTotales'] = 0

        listaPromociones = request.session['listaPromociones']
        # pprint.pprint(request.META['PATH_INFO'])
        # pprint.pprint('1' in request.META['PATH_INFO'])

        totalCms = 0
        totalCamAuto = 0
        totalCamInmobiliaria = 0
        totalSinPromocion = 0
        total2x1 = 0
        total3x1 = 0
        total3x1_2x2 = 0
        total4oMas = 0
        total5x1 = 0
        total7x3 = 0
        totalAg3x1 = 0
        totalAgCli = 0

        listaGrupo = []
        for data in listaPromociones:
            totalCms += data['CmsNeto']
            if 'mara de Automotores' in data['ValorAuxiliar']:
                totalCamAuto += data['CmsNeto']
                listaCamAuto.append(data)
            if 'mara Inmobiliaria' in data['ValorAuxiliar']:
                totalCamInmobiliaria += data['CmsNeto']
                listaCamInmobiliaria.append(data)
            if 'Sin Promoci' in data['ValorAuxiliar']:
                totalSinPromocion += data['CmsNeto']
                listaSinProm.append(data)
            if data['ValorAuxiliar'] == '2 publicaciones = 1 sin cargo':
                total2x1 += data['CmsNeto']
                lista2x1.append(data)
            if data['ValorAuxiliar'] == '3 publicaciones = 1 sin cargo':
                total3x1 += data['CmsNeto']
                lista3x1.append(data)
            if data['ValorAuxiliar'] == '3 publicaciones = 1 sin cargo(2x2)':
                total3x1_2x2 += data['CmsNeto']
                lista3x1_2x2.append(data)

            if '4 o mas d' in data['ValorAuxiliar']:
                total4oMas += data['CmsNeto']
                lista4omas.append(data)
            if data['ValorAuxiliar'] == '5 publicaciones = 1 Sin cargo' or data[
                'ValorAuxiliar'] == '5 Publicaciones = 1 sin cargo' or data[
                'ValorAuxiliar'] == '5 publicaciones = 1 sin cargo':
                total5x1 += data['CmsNeto']
                data['ValorAuxiliar'] = '5 publicaciones = 1 sin cargo'
                lista5x1.append(data)

            if data['ValorAuxiliar'] == '7 publicaciones = 3 sin cargo':
                total7x3 += data['CmsNeto']
                lista7x3.append(data)
            if data['ValorAuxiliar'] == 'Agencias publican 3 = 1 sin cargo':
                totalAg3x1 += data['CmsNeto']
                listaAg3x1.append(data)
            if data['ValorAuxiliar'] == 'Promo Agencia y Cliente':
                totalAgCli += data['CmsNeto']
                listaPromoAgCliente.append(data)

            if data['ValorAuxiliar'] == 'Convenio':
                listaConvenios.append(data)

        titulo = 'Todas las Promociones'
        listaTotal = listaPromociones

        if '1' in request.META['PATH_INFO']:
            titulo = 'Promoción 2 publicaciones = 1 sin cargo'
            listaGrupo = lista2x1
            # Título necesario para el excel
            request.session['titulo'] = 'Promocion: 2 publicaciones = 1 sin cargo'

        elif '2' in request.META['PATH_INFO']:
            titulo = 'Promoción 3 publicaciones = 1 sin cargo'
            listaGrupo = lista3x1
            request.session['titulo'] = 'Promocion 3 publicaciones = 1 sin cargo'

        elif '3' in request.META['PATH_INFO']:
            titulo = 'Promoción 3 publicaciones = 1 sin cargo [2x2]'
            listaGrupo = lista3x1_2x2
            request.session['titulo'] = 'Promocion 3 publicaciones = 1 sin cargo [2x2]'
        elif '4' in request.META['PATH_INFO']:
            titulo = 'Promoción 4 o más días = 50% Descuento'
            listaGrupo = lista4omas
            request.session['titulo'] = 'Promocion 4 o más días = 50% Descuento'
        elif '5' in request.META['PATH_INFO']:
            titulo = 'Promoción 5 publicaciones = 1 sin cargo'
            listaGrupo = lista5x1
            request.session['titulo'] = 'Promocion 5 publicaciones = 1 sin cargo'
        elif '6' in request.META['PATH_INFO']:
            titulo = 'Promoción 7 publicaciones = 3 sin cargo'
            listaGrupo = lista7x3
            request.session['titulo'] = 'Promocion 3 publicaciones = 1 sin cargo'
        elif '7' in request.META['PATH_INFO']:
            titulo = 'Promoción Agencias Publican 3 = 1 sin cargo'
            listaGrupo = listaAg3x1
            request.session['titulo'] = 'Promocion Agencias Publican 3 = 1 sin cargo'
        elif '8' in request.META['PATH_INFO']:
            titulo = 'Promoción Promo Agencia y Cliente'
            listaGrupo = listaPromoAgCliente
            request.session['titulo'] = 'Promocion Promo Agencia y Cliente'
        elif '9' in request.META['PATH_INFO']:
            titulo = 'Promoción Cámara de Automotores'
            listaGrupo = listaCamAuto
            request.session['titulo'] = 'Promocion Camara de Automotores'
        elif 'A' in request.META['PATH_INFO']:
            titulo = 'Promoción Cámara Inmobiliaria'
            listaGrupo = listaCamInmobiliaria
            request.session['titulo'] = 'Promocion Camara Inmobiliaria'
        elif 'B' in request.META['PATH_INFO']:
            titulo = 'Sin Promociones'
            listaGrupo = listaSinProm
            request.session['titulo'] = 'Sin Promociones'
        elif 'D' in request.META['PATH_INFO']:
            titulo = 'Convenios'
            listaGrupo = listaConvenios
            request.session['titulo'] = 'Convenios'

        fechaDesde = request.session['fechaDesde']
        fechaHasta = request.session['fechaHasta']
        codigoRemoto = request.session['codigoRemoto']

        listaPromocionesGrafico = []

        if totalCms != 0:
            porc2x1 = (total2x1 * 100) / totalCms
            listaPromocionesGrafico.append(dict(nombre='2 publicaciones = 1 sin Cargo', porc=porc2x1))

            porc3x1 = (total3x1 * 100) / totalCms
            listaPromocionesGrafico.append(dict(nombre='3 publicaciones = 1 sin Cargo', porc=porc3x1))

            porc3x1_2x2 = (total3x1_2x2 * 100) / totalCms
            listaPromocionesGrafico.append(dict(nombre='3 publicaciones = 1 sin Cargo [2x2]', porc=porc3x1_2x2))

            porcCamAuto = (totalCamAuto * 100) / totalCms
            listaPromocionesGrafico.append(dict(nombre='Camara Automotores', porc=porcCamAuto))

            porcInmobiliaria = (totalCamInmobiliaria * 100) / totalCms
            listaPromocionesGrafico.append(dict(nombre='Camara Inmobiliaria', porc=porcInmobiliaria))

            porc7x3 = (total7x3 * 100) / totalCms
            listaPromocionesGrafico.append(dict(nombre='7 publicaciones = 3 sin Cargo', porc=porc7x3))

            porc5x1 = (total5x1 * 100) / totalCms
            listaPromocionesGrafico.append(dict(nombre='5 publicaciones = 1 sin Cargo', porc=porc5x1))

            porc4oMas = (total4oMas * 100) / totalCms
            listaPromocionesGrafico.append(dict(nombre='4 o mas días 50% descuento', porc=porc4oMas))

            porcSinPromocion = (totalSinPromocion * 100) / totalCms
            listaPromocionesGrafico.append(dict(nombre='Sin Promocion', porc=porcSinPromocion))

            porcAgCli = (totalAgCli * 100) / totalCms
            listaPromocionesGrafico.append(dict(nombre='2 publicaciones = 1 sin Cargo', porc=porcAgCli))

            porcAg3x1 = (totalAg3x1 * 100) / totalCms
            listaPromocionesGrafico.append(dict(nombre='2 publicaciones = 1 sin Cargo', porc=porcAg3x1))

            listaPromocionesGrafico = json.dumps(listaPromocionesGrafico, cls=DjangoJSONEncoder)
        else:
            listaPromocionesGrafico = None

        if titulo == 'Todas las Promociones':
            request.session['titulo'] = 'Todas las Promociones'
            listaPromociones = json.dumps(listaTotal, cls=DjangoJSONEncoder)
            return render_to_response('reportesDePromociones/Promociones.html',
                                      {'listaPromocionesGrafico': listaPromocionesGrafico, 'fechaDesde': fechaDesde,
                                       'fechaHasta': fechaHasta,
                                       'codigoRemoto': codigoRemoto, 'tit': titulo},
                                      context_instance=RequestContext(request))

        request.session['headers'] = ['Ag. Cliente', 'Aviso', 'Cms Neto', 'V. Anuncio', 'Tot. Bruto', 'Total Desc.',
                                      'Neto Sin Iva', 'F. Factura', 'Nº Factura', 'Nº Pedido', 'Cod. Aviso',
                                      'Orden Publicidad']

        request.session['keys'] = ['AgenciaCliente', 'Aviso', 'CmsNeto', 'ValorAnuncio', 'TotalBruto', 'TotalDescuento',
                                   'NetoSinIva', 'fechafactura', 'nrofactura', 'nropedido', 'CodigoAviso',
                                   'OrdenPublicidad']

        listaGrupoOrdenada = sorted(listaGrupo, key=operator.itemgetter('Aviso'))
        request.session['listaPromocionesGrupo'] = listaGrupoOrdenada
        return render_to_response('reportesDePromociones/grupoPromociones.html',
                                  {'fechaDesde': fechaDesde, 'fechaHasta': fechaHasta,
                                   'codigoRemoto': codigoRemoto, 'tit': titulo},
                                  context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect('/promociones/formPromociones')


def json_GrupoPromociones(request):
    results = request.session['listaPromocionesGrupo']
    # request.session['titulo'] = 'Todas las Promociones'
    request.session['data'] = results
    jsony = json.dumps(results)
    return HttpResponse(jsony, content_type='application/json')


def json_AvisosFacturadosYPublicados(request):
    results = request.session['lista_resultados']
    jsony = json.dumps(results)
    return HttpResponse(jsony, content_type='application/json')


@login_required
def listaPromociones(request):
    return render_to_response('reportesDePromociones/listaPromociones.html', context_instance=RequestContext(request))


def jsonTotalVendedorxHora(request):
    listaVendedorHora = request.session['listaVendedorHora']

    results = listaVendedorHora

    totalesDeHora = []
    for key, val in itertools.groupby(listaVendedorHora, lambda v: v['horaCaptura']):
        cms = sum(item['cmsNetoxVendedor'] for item in val)
        totalesDeHora.append({'horaCaptura': key, 'cmsNetoxVendedor': cms})

    i = 0
    for key, val in itertools.groupby(listaVendedorHora, lambda v: v['horaCaptura']):
        DescCms = sum(item['netosinivaxVendedor'] for item in val)
        totalesDeHora[i].update({'netosinivaxVendedor': DescCms})
        i += 1

    # -----------------variables para cargar la data para el Excel-----------------------------------------------------------


    horaAnterior = listaVendedorHora[0]['horaCaptura']
    listaConTotales = []
    for data in listaVendedorHora:

        if horaAnterior != data['horaCaptura']:
            band = False
            i = 0
            while band == False:

                if totalesDeHora[i]['horaCaptura'] == horaAnterior:
                    filaDatos = totalesDeHora[i]

                    band = True
                i += 1

            listaConTotales.append(
                {'NombreVendedor': '', 'horaCaptura': 'Total', 'cmsNetoxVendedor': filaDatos['cmsNetoxVendedor'],
                 'netosinivaxVendedor': filaDatos['netosinivaxVendedor']})
            listaConTotales.append(
                {'NombreVendedor': '', 'horaCaptura': '', 'cmsNetoxVendedor': '', 'netosinivaxVendedor': ''})

            horaAnterior = data['horaCaptura']

        listaConTotales.append(data)
    band = False
    i = 0
    while not band:
        if totalesDeHora[i]['horaCaptura'] == horaAnterior:
            filaDatos = totalesDeHora[i]
            band = True
        i += 1
    listaConTotales.append(
        {'NombreVendedor': '', 'horaCaptura': 'Total', 'cmsNetoxVendedor': filaDatos['cmsNetoxVendedor'],
         'netosinivaxVendedor': filaDatos['netosinivaxVendedor']})

    request.session['data'] = listaConTotales

    #
    request.session['headers'] = ['Hora', 'Vendedor', 'Cms Netos', 'Neto Sin IVA']

    #
    request.session['titulo'] = 'Totales de Avisos Capturados por Vendedor'
    #
    request.session['keys'] = ['horaCaptura', 'NombreVendedor', 'cmsNetoxVendedor', 'netosinivaxVendedor']

    jsony = json.dumps(results)
    return HttpResponse(jsony, content_type='application/json')


def jsonTotalVendedorxHoraAjax(request):
    results = request.session['listaVendedorHoraSegunFormaDePago']



    # todo: cargar las variables para el excel


    jsony = json.dumps(results)
    return HttpResponse(jsony, content_type='application/json')


def viewFormVentasCaptura(request):
    # try:
    if request.method == 'POST':
        formulario = formVentasCaptura(request.POST)
        if formulario.is_valid():
            cursor = connections['default'].cursor()

            fechaDesde = formulario.cleaned_data['fechaDesde']
            df = DateFormat(fechaDesde)
            fechaDesde = df.format('Y-d-m')

            fechaDesdeModoLatino = df.format('d/m/Y')

            fechaHasta = formulario.cleaned_data['fechaHasta']
            df = DateFormat(fechaHasta)
            fechaHasta = df.format('Y-d-m')
            fechaHastaModoLatino = df.format('d/m/Y')

            request.session['fechaDesde'] = fechaDesdeModoLatino
            request.session['fechaHasta'] = fechaHastaModoLatino

            codRemoto = formulario.cleaned_data['codRemoto']

            if codRemoto == u'1':
                request.session['codigoRemoto'] = 'Chaco'
            else:
                request.session['codigoRemoto'] = 'Corrientes'

            formaDePago = formulario.cleaned_data['formaDePago']
            if formaDePago == u'1':
                cursor.execute(
                    "SELECT * FROM VentasDiaHora "
                    "where primerafechaapublicar >= %s and ultimafechaapublicar <= %s and codigoremoto = %s "
                    "and CodigoFmPago=4 order by aviso",
                    [fechaDesde, fechaHasta, codRemoto])
                request.session['criterio'] = "Cuenta Corriente"
            elif formaDePago == u'2':
                cursor.execute(
                    "SELECT * FROM VentasDiaHora "
                    "where primerafechaapublicar >= %s and ultimafechaapublicar <= %s and codigoremoto = %s "
                    "and CodigoFmPago=1 order by aviso",
                    [fechaDesde, fechaHasta, codRemoto])
                request.session['criterio'] = "Contado"
            else:
                cursor.execute(
                    "SELECT * FROM VentasDiaHora "
                    "where primerafechaapublicar >= %s and ultimafechaapublicar <= %s and codigoremoto = %s "
                    "and CodigoFmPago <> 1 and CodigoFmPago <> 4 order by aviso",
                    [fechaDesde, fechaHasta, codRemoto])
                request.session['criterio'] = "Otras Formas de Pago"

            listaAux = dictfetchall(cursor)

            request.session['lista_resultados'] = listaAux

            lista = []

            for data in (listaAux):
                data['cms_puro'] = None
                resultado = transformacionGenerica(data)
                if (data['fechafactura'] != None):
                    fechafactura = data['fechafactura'].strftime('%d/%m/%Y')
                else:
                    fechafactura = ''

                dictionary = dict(AgenciaCliente=data['AgenciaCliente'],
                                  Aviso=data['Aviso'], centimetros=data['centimetros'], DescCms=resultado['descCms'],
                                  CmsNeto=resultado['cmsNeto'],
                                  ValorAnuncio=resultado['valorAnuncio'], RecargoColor=data['RecargoColor'],
                                  RecargoLogo=data['RecargoLogo'],
                                  fechafactura=fechafactura,
                                  nrofactura=data['nrofactura'], nropedido=data['nropedido'],
                                  CodigoAviso=data['CodigoAviso'], OrdenPublicidad=data['OrdenPublicidad'],
                                  DescManual=resultado['descManual'], TotalRecargo=resultado['totalRecargo'],
                                  TotalBruto=resultado['totalBruto'],
                                  DescPromocion=data['DescPromocion'], DescConvenio=data['DescConvenio'],
                                  ComAgencia=data['DescAgencia'],
                                  DescAgencia=resultado['descAMano'], TotalDescuento=resultado['totalDescuento'],
                                  NetoSinIva=resultado['netoSinIva'],
                                  diaCaptura=data['DiaCaptura'], horaCaptura=data['HoraCaptura'])
                lista.append(dictionary)

            request.session['listaCaptura'] = lista

            return render_to_response('reportesDeVentasDiayHora/listaDiayHora.html',
                                      context_instance=RequestContext(request))
    else:
        formulario = formPromociones()
    return render_to_response('reportesDeVentasDiayHora/formVentasCaptura.html', {'formulario': formulario},
                              context_instance=RequestContext(request))
    # except Exception as e:
    #
    # return HttpResponseRedirect('/errorGeneral', {'mensaje': e.message,
    #                                                   'tipo': type(e)})  # , context_instance=RequestContext(request)


@login_required
def listaDiayHora(request):
    return render_to_response('reportesDeVentasDiayHora/listaDiayHora.html', context_instance=RequestContext(request))


@login_required
def capturaDiayHora(request):
    if request.session['listaCaptura'] != 0:
        lista = request.session['listaCaptura']

        if '0' in request.META['PATH_INFO']:

            listaOrdenada = sorted(lista, key=operator.itemgetter('diaCaptura'))
            listaPorDia = []
            Total_TotalCms = 0
            Total_DescCms = 0
            Total_CmsNeto = 0
            Total_TotalBruto = 0
            Total_TotalDescuento = 0
            Total_NetoSinIva = 0
            for key, val in itertools.groupby(listaOrdenada, lambda v: v['diaCaptura']):
                TotalCms = sum(item['centimetros'] for item in val)
                Total_TotalCms += TotalCms
                # aca creo la lista por primera vez con los N tipo de avisos que existen
                listaPorDia.append({'diaCaptura': key, 'TotalCms': TotalCms})

            i = 0
            for key, val in itertools.groupby(listaOrdenada, lambda v: v['diaCaptura']):
                DescCms = sum(item['DescCms'] for item in val)
                Total_DescCms += DescCms
                listaPorDia[i].update({'DescCms': DescCms})
                i += 1

            i = 0
            for key, val in itertools.groupby(listaOrdenada, lambda v: v['diaCaptura']):
                CmsNeto = sum(item['CmsNeto'] for item in val)
                Total_CmsNeto += CmsNeto
                listaPorDia[i].update({'CmsNeto': CmsNeto})
                i += 1

            i = 0
            for key, val in itertools.groupby(listaOrdenada, lambda v: v['diaCaptura']):
                TotalBruto = sum(item['TotalBruto'] for item in val)
                Total_TotalBruto += TotalBruto
                listaPorDia[i].update({'TotalBruto': TotalBruto})
                i += 1

            i = 0
            for key, val in itertools.groupby(listaOrdenada, lambda v: v['diaCaptura']):
                TotalDescuento = sum(item['TotalDescuento'] for item in val)
                Total_TotalDescuento += TotalDescuento
                listaPorDia[i].update({'TotalDescuento': TotalDescuento})
                i += 1

            i = 0
            for key, val in itertools.groupby(listaOrdenada, lambda v: v['diaCaptura']):
                NetoSinIva = sum(item['NetoSinIva'] for item in val)
                Total_NetoSinIva += NetoSinIva
                listaPorDia[i].update({'NetoSinIva': NetoSinIva})
                i += 1

            listaPorDia = sorted(listaPorDia, key=lambda k: k['TotalCms'], reverse=True)

            total_porcentajeTotalCms = 0
            total_porcentajeNetoSinIva = 0

            for data in listaPorDia:
                porcentajeTotalCms = 0
                if Total_TotalCms != 0:
                    porcentajeTotalCms = (data['TotalCms'] / Total_TotalCms) * 100
                    total_porcentajeTotalCms += porcentajeTotalCms

                porcentajeNetoSinIva = 0
                if Total_NetoSinIva != 0:
                    porcentajeNetoSinIva = (data['NetoSinIva'] / Total_NetoSinIva) * 100
                    total_porcentajeNetoSinIva += porcentajeNetoSinIva

                data.update({'PorcentajeCms': porcentajeTotalCms, 'PorcentajeNetoSinIva': porcentajeNetoSinIva})

            listaPorDia.append({'diaCaptura': '', 'TotalCms': '', 'DescCms': '', 'CmsNeto': '', 'TotalBruto': '',
                                'TotalDescuento': '', 'NetoSinIva': '', 'PorcentajeCms': '',
                                'PorcentajeNetoSinIva': ''})

            listaPorDia.append({'diaCaptura': 'Total General', 'TotalCms': Total_TotalCms, 'DescCms': Total_DescCms,
                                'CmsNeto': Total_CmsNeto, 'TotalBruto': Total_TotalBruto,
                                'TotalDescuento': Total_TotalDescuento, 'NetoSinIva': Total_NetoSinIva,
                                'PorcentajeCms': total_porcentajeTotalCms,
                                'PorcentajeNetoSinIva': total_porcentajeNetoSinIva})

            listaDiaHora = json.dumps(listaPorDia, cls=DjangoJSONEncoder)
            agrupacion = 'diaCaptura'
            titulo = 'Dia Captura segun ' + request.session['criterio']

            # Primera Columna y título necesario para el excel
            request.session['titulo'] = 'Captura de Avisos por Dia segun ' + request.session['criterio']
            request.session['data'] = listaPorDia
            request.session['reporteConTotales'] = len(listaPorDia)
            primeraColumna = 'Dia'
            keyPrimeraColumna = 'diaCaptura'

        elif '1' in request.META['PATH_INFO']:

            listaOrdenada = sorted(lista, key=operator.itemgetter('horaCaptura'))
            listaPorHora = []
            Total_TotalCms = 0
            Total_DescCms = 0
            Total_CmsNeto = 0
            Total_TotalBruto = 0
            Total_TotalDescuento = 0
            Total_NetoSinIva = 0
            for key, val in itertools.groupby(listaOrdenada, lambda v: v['horaCaptura']):
                TotalCms = sum(item['centimetros'] for item in val)
                Total_TotalCms += TotalCms
                # aca creo la lista por primera vez con los N tipo de avisos que existen
                listaPorHora.append({'horaCaptura': key, 'TotalCms': TotalCms})

            i = 0
            for key, val in itertools.groupby(listaOrdenada, lambda v: v['horaCaptura']):
                DescCms = sum(item['DescCms'] for item in val)
                Total_DescCms += DescCms
                listaPorHora[i].update({'DescCms': DescCms})
                i += 1

            i = 0
            for key, val in itertools.groupby(listaOrdenada, lambda v: v['horaCaptura']):
                CmsNeto = sum(item['CmsNeto'] for item in val)
                Total_CmsNeto += CmsNeto
                listaPorHora[i].update({'CmsNeto': CmsNeto})
                i += 1

            i = 0
            for key, val in itertools.groupby(listaOrdenada, lambda v: v['horaCaptura']):
                TotalBruto = sum(item['TotalBruto'] for item in val)
                Total_TotalBruto += TotalBruto
                listaPorHora[i].update({'TotalBruto': TotalBruto})
                i += 1

            i = 0
            for key, val in itertools.groupby(listaOrdenada, lambda v: v['horaCaptura']):
                TotalDescuento = sum(item['TotalDescuento'] for item in val)
                Total_TotalDescuento += TotalDescuento
                listaPorHora[i].update({'TotalDescuento': TotalDescuento})
                i += 1

            i = 0
            for key, val in itertools.groupby(listaOrdenada, lambda v: v['horaCaptura']):
                NetoSinIva = sum(item['NetoSinIva'] for item in val)
                Total_NetoSinIva += NetoSinIva
                listaPorHora[i].update({'NetoSinIva': NetoSinIva})
                i += 1

            listaPorHora = sorted(listaPorHora, key=lambda k: k['TotalCms'], reverse=True)

            total_porcentajeTotalCms = 0
            total_porcentajeNetoSinIva = 0
            for data in listaPorHora:
                porcentajeTotalCms = 0
                if Total_TotalCms != 0:
                    porcentajeTotalCms = (data['TotalCms'] / Total_TotalCms) * 100
                    total_porcentajeTotalCms += porcentajeTotalCms

                porcentajeNetoSinIva = 0
                if Total_NetoSinIva != 0:
                    porcentajeNetoSinIva = (data['NetoSinIva'] / Total_NetoSinIva) * 100
                    total_porcentajeNetoSinIva += porcentajeNetoSinIva

                data.update({'PorcentajeCms': porcentajeTotalCms, 'PorcentajeNetoSinIva': porcentajeNetoSinIva})

            listaPorHora.append({'horaCaptura': '', 'TotalCms': '', 'DescCms': '', 'CmsNeto': '', 'TotalBruto': '',
                                 'TotalDescuento': '', 'NetoSinIva': '', 'PorcentajeCms': '',
                                 'PorcentajeNetoSinIva': ''})

            listaPorHora.append({'horaCaptura': 'Total General', 'TotalCms': Total_TotalCms, 'DescCms': Total_DescCms,
                                 'CmsNeto': Total_CmsNeto, 'TotalBruto': Total_TotalBruto,
                                 'TotalDescuento': Total_TotalDescuento, 'NetoSinIva': Total_NetoSinIva,
                                 'PorcentajeCms': total_porcentajeTotalCms,
                                 'PorcentajeNetoSinIva': total_porcentajeNetoSinIva})
            listaDiaHora = json.dumps(listaPorHora, cls=DjangoJSONEncoder)
            agrupacion = 'horaCaptura'
            titulo = 'Hora Captura segun ' + request.session['criterio']

            # excel
            request.session['titulo'] = 'Captura de Avisos por Hora segun ' + request.session['criterio']
            request.session['data'] = listaPorHora
            request.session['reporteConTotales'] = len(listaPorHora)
            primeraColumna = 'Hora'
            keyPrimeraColumna = agrupacion

        codRemoto = request.session['codigoRemoto']
        fechaDesde = request.session['fechaDesde']
        fechaHasta = request.session['fechaHasta']

        # Datos necesarios para el Excel
        request.session['headers'] = [primeraColumna, 'Total Cms', 'Desc Cms', 'Cms Neto', 'Total Bruto', 'Total Desc.',
                                      'Neto sin Iva', '% Centimetros', '% Neto sin Iva']
        request.session['keys'] = [keyPrimeraColumna, 'TotalCms', 'DescCms', 'CmsNeto', 'TotalBruto', 'TotalDescuento',
                                   'NetoSinIva', 'PorcentajeCms', 'PorcentajeNetoSinIva']

        return render_to_response('reportesDeVentasDiayHora/diaHoraCaptura.html',
                                  {'listaDiaHora': listaDiaHora, 'agrupacion': agrupacion, 'tit': titulo,
                                   'codRemoto': codRemoto, 'fechaDesde': fechaDesde, 'fechaHasta': fechaHasta},
                                  context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect('/ventasDiayHora/formVentasCaptura')


@login_required
def listaVentasPorVendedor(request):
    return render_to_response('reportesVendedor/listaVentasPorVendedor.html', context_instance=RequestContext(request))


@login_required
def formVentasVendedor(request):
    try:

        if request.method == 'POST':
            formulario = formVentasCaptura(request.POST)

            if formulario.is_valid():

                cursor = connections['default'].cursor()
                fechaDesde = formulario.cleaned_data['fechaDesde']
                df = DateFormat(fechaDesde)
                fechaDesde = df.format('Y-d-m')

                # Se hace para verificar que se guarde un mes
                request.session['dia'] = df.format('d')

                # Para poder guardar en la BD
                request.session['mesDesdeAGuardar'] = df.format('m')
                request.session['anioDesdeAGuardar'] = df.format('Y')

                fechaDesdeModoLatino = df.format('d/m/Y')

                fechaHasta = formulario.cleaned_data['fechaHasta']
                df = DateFormat(fechaHasta)
                fechaHasta = df.format('Y-d-m')

                #Para poder guardar en la BD
                request.session['mesHastaAGuardar'] = df.format('m')
                request.session['anioHastaAGuardar'] = df.format('y')

                fechaHastaModoLatino = df.format('d/m/Y')
                # formaDePago = 1 # No importa el valor, para el script SQL es indiferente.

                request.session['fechaDesde'] = fechaDesdeModoLatino
                request.session['fechaHasta'] = fechaHastaModoLatino

                codRemoto = formulario.cleaned_data['codRemoto']
                if codRemoto == u'1':
                    request.session['codigoRemoto'] = 'Chaco'
                else:
                    request.session['codigoRemoto'] = 'Corrientes'

                cursor.execute("SELECT * FROM ventasDiaHoraVendedor where primerafechaapublicar >= %s and "
                               "ultimafechaapublicar <= %s and codigoremoto=%s",
                               (fechaDesde, fechaHasta, codRemoto))

                listaBruta = []
                for data in dictfetchall(cursor):
                    dictionary = dict(HoraCaptura=data['HoraCaptura'], AgenciaCliente=data['AgenciaCliente'],
                                      #Codigo=data['Codigo'],
                                      Aviso=data['Aviso'], centimetros=data['centimetros'],
                                      ValorAnuncio=data['ValorAnuncio'], RecargoColor=data['RecargoColor'],
                                      RecargoLogo=data['RecargoLogo'], DescPromocion=data['DescPromocion'],
                                      DescConvenio=data['DescConvenio'],
                                      DescAgencia=data['DescAgencia'], DescuentoAMano=data['DescuentoAMano'],
                                      fechafactura=data['fechafactura'],
                                      nrofactura=data['nrofactura'], nropedido=data['nropedido'],
                                      CodigoAviso=data['CodigoAviso'],
                                      OrdenPublicidad=data['OrdenPublicidad'],
                                      ValorSinImpuestos=data['ValorSinImpuestos'],
                                      valorapagar=data['valorapagar'], SupSaCh=data['SupSaCh'],
                                      formaDePago=data['CodigoFmPago'],
                                      diaCaptura=data['DiaCaptura'], nombreVendedor=data['nombreVendedor'])
                    listaBruta.append(dictionary)

                request.session['listaBrutaParaVendedores'] = listaBruta
                return render_to_response('reportesVendedor/listaVentasPorVendedor.html',
                                          context_instance=RequestContext(request))


        else:
            formulario = formVentasCaptura()

        return render_to_response('reportesVendedor/formVentasVendedor.html', {'formulario': formulario},
                                  context_instance=RequestContext(request))
    except Exception as e:

        return HttpResponseRedirect('/errorGeneral', {'mensaje': e.message,
                                                      'tipo': type(e)})  # , context_instance=RequestContext(request)


@login_required
def ventasVendedorPorHora(request):
    if request.session['listaBrutaParaVendedores'] != 0:

        listaBruta = request.session['listaBrutaParaVendedores']
        listaAuxiliar = []
        cmsNetoxVendedorxHora = 0
        netosinivaxVendedorxHora = 0

        if listaBruta != []:

            listaBrutaOrdenada = sorted(listaBruta, key=operator.itemgetter('HoraCaptura'))
            horaAnterior = int(listaBrutaOrdenada[0]['HoraCaptura'])
            # vendedorAnterior=listaBrutaOrdenada[0]['nombreVendedor']

            listaVendedorHora = []
            for data in listaBrutaOrdenada:

                if data['RecargoColor'] == None:
                    data['RecargoColor'] = 0

                if data['RecargoLogo'] == None:
                    data['RecargoLogo'] = 0

                valorAnuncio = data['ValorAnuncio']
                if data['SupSaCh'] == 109:
                    valorAnuncio = data['ValorAnuncio'] - data['RecargoColor']

                descManual = 0
                if data['DescuentoAMano'] < 0:
                    descManual = ((valorAnuncio + data['RecargoColor'] + data['RecargoLogo']) -
                                  (data['DescPromocion'] + data['DescConvenio'] + data['DescAgencia'])) * data[
                                     'DescuentoAMano'] * (-1) / 100

                totalRecargo = data['RecargoColor'] + data['RecargoLogo'] + descManual

                totalBruto = valorAnuncio + totalRecargo

                descCms = 0
                if totalBruto != 0:
                    descCms = math.ceil((round((data['DescPromocion'] / totalBruto), 2)) * data['centimetros'])

                cmsNeto = data['centimetros'] - descCms

                descAMano = 0
                if data['DescuentoAMano'] > 0:
                    descAMano = ((((valorAnuncio + data['RecargoColor'] + data['RecargoLogo'] + descManual) -
                                   (data['DescPromocion'] + data['DescConvenio'] + data['DescAgencia'])) *
                                  data['DescuentoAMano']) / 100)

                totalDescuento = data['DescPromocion'] + data['DescConvenio'] + descAMano + data['DescAgencia']

                netoSinIva = totalBruto - totalDescuento

                hora = data['HoraCaptura']

                # diccionarioHoraVendedor = dict(HoraCaptura=hora, nombreVendedor=data['nombreVendedor'], CmsNeto=cmsNeto, NetoSinIva=netoSinIva)
                # lis.append(diccionarioHoraVendedor)

                if horaAnterior != hora:

                    listaAuxiliarOrdenada = sorted(listaAuxiliar, key=operator.itemgetter('nombreVendedor'))

                    vendedorAnterior = listaAuxiliarOrdenada[0]['nombreVendedor']

                    for elemento in listaAuxiliarOrdenada:
                        vendedorActual = elemento['nombreVendedor']
                        # pprint.pprint(vendedorActual==vendedorAnterior)
                        if (vendedorAnterior != vendedorActual):
                            diccionarioVendedorxHora = dict(NombreVendedor=vendedorAnterior, horaCaptura=horaAnterior,
                                                            cmsNetoxVendedor=cmsNetoxVendedorxHora,
                                                            netosinivaxVendedor=netosinivaxVendedorxHora)

                            listaVendedorHora.append(diccionarioVendedorxHora)
                            vendedorAnterior = vendedorActual
                            cmsNetoxVendedorxHora = 0
                            netosinivaxVendedorxHora = 0

                        cmsNetoxVendedorxHora = cmsNetoxVendedorxHora + elemento['CmsNeto']
                        netosinivaxVendedorxHora = netosinivaxVendedorxHora + elemento['NetoSinIva']

                    diccionarioVendedorxHora = dict(NombreVendedor=vendedorAnterior, horaCaptura=horaAnterior,
                                                    cmsNetoxVendedor=cmsNetoxVendedorxHora,
                                                    netosinivaxVendedor=netosinivaxVendedorxHora)

                    listaVendedorHora.append(diccionarioVendedorxHora)

                    cmsNetoxVendedorxHora = 0
                    netosinivaxVendedorxHora = 0
                    listaAuxiliar = []
                    diccionarioHoraVendedor = dict()

                diccionarioHoraVendedor = dict(horaCaptura=hora, nombreVendedor=data['nombreVendedor'], CmsNeto=cmsNeto,
                                               NetoSinIva=netoSinIva)
                listaAuxiliar.append(diccionarioHoraVendedor)

                horaAnterior = hora
                ####################################################################################################
            ##### Se repite este codigo para ir discriminando los vendedores la la última hora que fue almacenado en Lista auxiliar.
            listaAuxiliarOrdenada = sorted(listaAuxiliar, key=operator.itemgetter('nombreVendedor'))
            vendedorAnterior = listaAuxiliarOrdenada[0]['nombreVendedor']

            cmsNetoxVendedorxHora = 0
            netosinivaxVendedorxHora = 0
            for elemento in listaAuxiliarOrdenada:
                vendedorActual = elemento['nombreVendedor']
                # pprint.pprint(vendedorActual==vendedorAnterior)
                if (vendedorAnterior != vendedorActual):
                    diccionarioVendedorxHora = dict(NombreVendedor=vendedorAnterior, horaCaptura=horaAnterior,
                                                    cmsNetoxVendedor=cmsNetoxVendedorxHora,
                                                    netosinivaxVendedor=netosinivaxVendedorxHora)

                    listaVendedorHora.append(diccionarioVendedorxHora)
                    vendedorAnterior = vendedorActual
                    cmsNetoxVendedorxHora = 0
                    netosinivaxVendedorxHora = 0

                cmsNetoxVendedorxHora = cmsNetoxVendedorxHora + elemento['CmsNeto']
                netosinivaxVendedorxHora = netosinivaxVendedorxHora + elemento['NetoSinIva']

            diccionarioVendedorxHora = dict(NombreVendedor=vendedorAnterior, horaCaptura=horaAnterior,
                                            cmsNetoxVendedor=cmsNetoxVendedorxHora,
                                            netosinivaxVendedor=netosinivaxVendedorxHora)

            listaVendedorHora.append(diccionarioVendedorxHora)

            totalesDeHora = []
            totalCms = 0
            for key, val in itertools.groupby(listaVendedorHora, lambda v: v['horaCaptura']):
                cms = sum(item['cmsNetoxVendedor'] for item in val)
                totalCms += cms
                totalesDeHora.append({'horaCaptura': key, 'totalCms': totalCms})

            i = 0
            totalNetoSinIva = 0
            for key, val in itertools.groupby(listaVendedorHora, lambda v: v['horaCaptura']):
                DescCms = sum(item['netosinivaxVendedor'] for item in val)
                totalNetoSinIva += DescCms
                totalesDeHora[i].update({'netosinivaxVendedor': DescCms})
                i += 1

            request.session['listaDeTotalesVendedorHora'] = totalesDeHora

            request.session['listaVendedorHoraSegunFormaDePago'] = listaVendedorHora

            request.session['listaVendedorHora'] = listaVendedorHora
        else:
            request.session['listaVendedorHora'] = []

        fechaDesde = request.session['fechaDesde']
        fechaHasta = request.session['fechaHasta']
        codigoRemoto = request.session['codigoRemoto']

        tit = 'Total de Vendedor por Franja Horaria'
        request.session['titulo'] = tit
        # pprint.pprint(listaVendedorHora)
        return render_to_response('reportesVendedor/vendedorxHora.html', {'fechaDesde': fechaDesde,
                                                                          'fechaHasta': fechaHasta,
                                                                          'codigoRemoto': codigoRemoto, 'tit': tit},
                                  context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect('/reportesVendedor/formVentasVendedor')


@login_required
def ajaxVendedorHoraFormasDePago(request):
    listaVendedorHora = request.session['listaBrutaParaVendedores']
    request.session['reporteConTotales'] = 0

    listaDeListasPorHora = []
    listaDeHoras = []
    listaDeVendedores = []

    if request.method == 'POST' and request.is_ajax():

        seleccion = request.POST["seleccion"]

        listaSegunFormaDePago = []


        # 1: Contado---------------2: Cta Cte -------------- 3: Cortesias ------- 4: Reposición -------------5: Compensación
        if seleccion == u'0':
            listaVendedorHora = request.session['listaVendedorHora']

            totalesDeHora = []
            for key, val in itertools.groupby(listaVendedorHora, lambda v: v['horaCaptura']):
                cms = sum(item['cmsNetoxVendedor'] for item in val)
                totalesDeHora.append({'horaCaptura': key, 'cmsNetoxVendedor': cms})

            i = 0
            for key, val in itertools.groupby(listaVendedorHora, lambda v: v['horaCaptura']):
                DescCms = sum(item['netosinivaxVendedor'] for item in val)
                totalesDeHora[i].update({'netosinivaxVendedor': DescCms})
                i += 1

            # -----------------variables para cargar la data para el Excel-----------------------------------------------------------


            horaAnterior = listaVendedorHora[0]['horaCaptura']
            listaConTotales = []
            for data in listaVendedorHora:

                if horaAnterior != data['horaCaptura']:
                    band = False
                    i = 0
                    while band == False:

                        if totalesDeHora[i]['horaCaptura'] == horaAnterior:
                            filaDatos = totalesDeHora[i]

                            band = True
                        i += 1

                    listaConTotales.append({'NombreVendedor': '', 'horaCaptura': 'Total',
                                            'cmsNetoxVendedor': filaDatos['cmsNetoxVendedor'],
                                            'netosinivaxVendedor': filaDatos['netosinivaxVendedor']})
                    listaConTotales.append(
                        {'NombreVendedor': '', 'horaCaptura': '', 'cmsNetoxVendedor': '', 'netosinivaxVendedor': ''})

                    horaAnterior = data['horaCaptura']

                listaConTotales.append(data)
            band = False
            i = 0
            while not band:
                if totalesDeHora[i]['horaCaptura'] == horaAnterior:
                    filaDatos = totalesDeHora[i]
                    band = True
                i += 1
            listaConTotales.append(
                {'NombreVendedor': '', 'horaCaptura': 'Total', 'cmsNetoxVendedor': filaDatos['cmsNetoxVendedor'],
                 'netosinivaxVendedor': filaDatos['netosinivaxVendedor']})

            request.session['data'] = listaConTotales
            #
            request.session['headers'] = ['Hora', 'Vendedor', 'Cms Netos', 'Neto Sin IVA']
            #
            request.session['titulo'] = 'Totales de Cms Capturados por Vendedor'
            #
            request.session['keys'] = ['horaCaptura', 'NombreVendedor', 'cmsNetoxVendedor', 'netosinivaxVendedor']

            return HttpResponse(json.dumps({'seleccion': seleccion}),
                                content_type='application/javascript')  #reemplazo el simplejason x json

        elif seleccion == u'1':
            for data in listaVendedorHora:
                if data['formaDePago'] == 1:
                    listaSegunFormaDePago.append(data)

            # esta variable es para el titulo del grid.
            tipo = 'Contado/Efectivo'

        elif seleccion == u'2':
            for data in listaVendedorHora:
                if data['formaDePago'] == 4:
                    listaSegunFormaDePago.append(data)

            tipo = 'Cuenta Corriente'

        elif seleccion == u'3':
            for data in listaVendedorHora:
                if data['formaDePago'] == 7:
                    listaSegunFormaDePago.append(data)
            tipo = 'Cortesias'

        elif seleccion == u'4':
            for data in listaVendedorHora:
                if data['formaDePago'] == 8:
                    listaSegunFormaDePago.append(data)
            tipo = 'Reposicion'

        else:
            for data in listaVendedorHora:
                if data['formaDePago'] == 6:
                    listaSegunFormaDePago.append(data)
            tipo = 'Compensacion'

        listaAuxiliar = []
        cmsNetoxVendedorxHora = 0
        netosinivaxVendedorxHora = 0

        if listaSegunFormaDePago != []:

            listaBrutaOrdenada = sorted(listaSegunFormaDePago, key=operator.itemgetter('HoraCaptura'))
            horaAnterior = int(listaBrutaOrdenada[0]['HoraCaptura'])
            # vendedorAnterior=listaBrutaOrdenada[0]['nombreVendedor']

            listaVendedorHora = []
            for data in listaBrutaOrdenada:

                if data['RecargoColor'] == None:
                    data['RecargoColor'] = 0

                if data['RecargoLogo'] == None:
                    data['RecargoLogo'] = 0

                valorAnuncio = data['ValorAnuncio']
                if data['SupSaCh'] == 109:
                    valorAnuncio = data['ValorAnuncio'] - data['RecargoColor']

                descManual = 0
                if data['DescuentoAMano'] < 0:
                    descManual = ((valorAnuncio + data['RecargoColor'] + data['RecargoLogo']) -
                                  (data['DescPromocion'] + data['DescConvenio'] + data['DescAgencia'])) * data[
                                     'DescuentoAMano'] * (-1) / 100

                totalRecargo = data['RecargoColor'] + data['RecargoLogo'] + descManual

                totalBruto = valorAnuncio + totalRecargo

                descCms = 0
                if totalBruto != 0:
                    descCms = math.ceil((round((data['DescPromocion'] / totalBruto), 2)) * data['centimetros'])

                # else:
                # cmsNeto = 0

                cmsNeto = data['centimetros'] - descCms

                descAMano = 0
                if data['DescuentoAMano'] > 0:
                    descAMano = ((((valorAnuncio + data['RecargoColor'] + data['RecargoLogo'] + descManual) -
                                   (data['DescPromocion'] + data['DescConvenio'] + data['DescAgencia'])) *
                                  data['DescuentoAMano']) / 100)

                totalDescuento = data['DescPromocion'] + data['DescConvenio'] + descAMano + data['DescAgencia']

                netoSinIva = totalBruto - totalDescuento

                hora = data['HoraCaptura']

                # diccionarioHoraVendedor = dict(HoraCaptura=hora, nombreVendedor=data['nombreVendedor'], CmsNeto=cmsNeto, NetoSinIva=netoSinIva)
                # lis.append(diccionarioHoraVendedor)

                if horaAnterior != hora:

                    listaDeHoras.append(horaAnterior)

                    listaAuxiliarOrdenada = sorted(listaAuxiliar, key=operator.itemgetter('nombreVendedor'))

                    listaAux = []
                    totalCms = 0
                    for key, val in itertools.groupby(listaAuxiliarOrdenada, lambda v: v['nombreVendedor']):
                        cms = sum(item['CmsNeto'] for item in val)
                        totalCms += cms
                        listaAux.append({'CmsNeto': cms, 'nombreVendedor': key})

                    listaDeListasPorHora.append(listaAux)

                    vendedorAnterior = listaAuxiliarOrdenada[0]['nombreVendedor']

                    for elemento in listaAuxiliarOrdenada:
                        vendedorActual = elemento['nombreVendedor']
                        # pprint.pprint(vendedorActual==vendedorAnterior)
                        if (vendedorAnterior != vendedorActual):
                            if vendedorAnterior not in listaDeVendedores:
                                listaDeVendedores.append(vendedorAnterior)

                            diccionarioVendedorxHora = dict(NombreVendedor=vendedorAnterior, horaCaptura=horaAnterior,
                                                            cmsNetoxVendedor=cmsNetoxVendedorxHora,
                                                            netosinivaxVendedor=netosinivaxVendedorxHora)

                            listaVendedorHora.append(diccionarioVendedorxHora)
                            vendedorAnterior = vendedorActual
                            cmsNetoxVendedorxHora = 0
                            netosinivaxVendedorxHora = 0

                        cmsNetoxVendedorxHora = cmsNetoxVendedorxHora + elemento['CmsNeto']
                        netosinivaxVendedorxHora = netosinivaxVendedorxHora + elemento['NetoSinIva']

                    if vendedorAnterior not in listaDeVendedores:
                        listaDeVendedores.append(vendedorAnterior)

                    diccionarioVendedorxHora = dict(NombreVendedor=vendedorAnterior, horaCaptura=horaAnterior,
                                                    cmsNetoxVendedor=cmsNetoxVendedorxHora,
                                                    netosinivaxVendedor=netosinivaxVendedorxHora)

                    listaVendedorHora.append(diccionarioVendedorxHora)

                    cmsNetoxVendedorxHora = 0
                    netosinivaxVendedorxHora = 0
                    listaAuxiliar = []
                    diccionarioHoraVendedor = dict()

                diccionarioHoraVendedor = dict(horaCaptura=hora, nombreVendedor=data['nombreVendedor'], CmsNeto=cmsNeto,
                                               NetoSinIva=netoSinIva)
                listaAuxiliar.append(diccionarioHoraVendedor)

                horaAnterior = hora

            ###########################################################################################
            ##### Se repite este codigo para ir discriminando los vendedores la la última hora que fue almacenado en Lista auxiliar.

            listaDeHoras.append(horaAnterior)
            listaAuxiliarOrdenada = sorted(listaAuxiliar, key=operator.itemgetter('nombreVendedor'))

            ############# ---------- Para lista de lista de horas ----------------------####################
            listaAux = []
            totalCms = 0
            for key, val in itertools.groupby(listaAuxiliarOrdenada, lambda v: v['nombreVendedor']):
                cms = sum(item['CmsNeto'] for item in val)
                totalCms += cms
                listaAux.append({'CmsNeto': cms, 'nombreVendedor': key})

            listaDeListasPorHora.append(listaAux)

            #########--------------------------------------------------------------#############
            vendedorAnterior = listaAuxiliarOrdenada[0]['nombreVendedor']

            cmsNetoxVendedorxHora = 0
            netosinivaxVendedorxHora = 0
            for elemento in listaAuxiliarOrdenada:
                vendedorActual = elemento['nombreVendedor']
                # pprint.pprint(vendedorActual==vendedorAnterior)
                if (vendedorAnterior != vendedorActual):
                    if vendedorAnterior not in listaDeVendedores:
                        listaDeVendedores.append(vendedorAnterior)

                    diccionarioVendedorxHora = dict(NombreVendedor=vendedorAnterior, horaCaptura=horaAnterior,
                                                    cmsNetoxVendedor=cmsNetoxVendedorxHora,
                                                    netosinivaxVendedor=netosinivaxVendedorxHora)

                    listaVendedorHora.append(diccionarioVendedorxHora)
                    vendedorAnterior = vendedorActual
                    cmsNetoxVendedorxHora = 0
                    netosinivaxVendedorxHora = 0

                cmsNetoxVendedorxHora = cmsNetoxVendedorxHora + elemento['CmsNeto']
                netosinivaxVendedorxHora = netosinivaxVendedorxHora + elemento['NetoSinIva']

            if vendedorAnterior not in listaDeVendedores:
                listaDeVendedores.append(vendedorAnterior)

            diccionarioVendedorxHora = dict(NombreVendedor=vendedorAnterior, horaCaptura=horaAnterior,
                                            cmsNetoxVendedor=cmsNetoxVendedorxHora,
                                            netosinivaxVendedor=netosinivaxVendedorxHora)

            listaVendedorHora.append(diccionarioVendedorxHora)



            # Todo lo siguiente comentadado lo hago para mostrar los totalizadores por hora en el excel como se muestran en el jqgrid.

            totalesDeHora = []
            totalCms = 0
            for key, val in itertools.groupby(listaVendedorHora, lambda v: v['horaCaptura']):
                cms = sum(item['cmsNetoxVendedor'] for item in val)
                totalesDeHora.append({'horaCaptura': key, 'cmsNetoxVendedor': cms})

            i = 0
            totalNetoSinIva = 0
            for key, val in itertools.groupby(listaVendedorHora, lambda v: v['horaCaptura']):
                DescCms = sum(item['netosinivaxVendedor'] for item in val)
                totalesDeHora[i].update({'netosinivaxVendedor': DescCms})
                i += 1




            #-----------------variables para cargar la data para el Excel-----------------------------------------------------------


            horaAnterior = listaVendedorHora[0]['horaCaptura']
            listaConTotales = []
            for data in listaVendedorHora:

                if horaAnterior != data['horaCaptura']:
                    band = False
                    i = 0
                    while band == False:

                        if totalesDeHora[i]['horaCaptura'] == horaAnterior:
                            filaDatos = totalesDeHora[i]

                            band = True
                        i += 1

                    listaConTotales.append({'NombreVendedor': '', 'horaCaptura': 'Total',
                                            'cmsNetoxVendedor': filaDatos['cmsNetoxVendedor'],
                                            'netosinivaxVendedor': filaDatos['netosinivaxVendedor']})
                    listaConTotales.append(
                        {'NombreVendedor': '', 'horaCaptura': '', 'cmsNetoxVendedor': '', 'netosinivaxVendedor': ''})

                    horaAnterior = data['horaCaptura']

                listaConTotales.append(data)
            band = False
            i = 0
            while not band:
                if totalesDeHora[i]['horaCaptura'] == horaAnterior:
                    filaDatos = totalesDeHora[i]
                    band = True
                i += 1
            listaConTotales.append(
                {'NombreVendedor': '', 'horaCaptura': 'Total', 'cmsNetoxVendedor': filaDatos['cmsNetoxVendedor'],
                 'netosinivaxVendedor': filaDatos['netosinivaxVendedor']})

            request.session['data'] = listaConTotales

            request.session['titulo'] = 'Totales de Avisos de ' + tipo

            request.session['keys'] = ['horaCaptura', 'NombreVendedor', 'cmsNetoxVendedor', 'netosinivaxVendedor']


            #---------------------------------------------------------------------------------------------------------------------------


            request.session['listaVendedorHoraSegunFormaDePago'] = listaVendedorHora


        else:
            request.session['listaVendedorHoraSegunFormaDePago'] = []

        listaDeListasPorHora = json.dumps(listaDeListasPorHora, cls=DjangoJSONEncoder)
        listaDeHoras = json.dumps(listaDeHoras, cls=DjangoJSONEncoder)
        listaDeVendedores = json.dumps(listaDeVendedores, cls=DjangoJSONEncoder)
        return HttpResponse(
            json.dumps({'tipo': tipo, 'listaDeListasPorHora': listaDeListasPorHora, 'listaDeHoras': listaDeHoras,
                        'listaDeVendedores': listaDeVendedores}),
            content_type='application/javascript')  # reemplazo el simplejason x json

    fechaDesde = request.session['fechaDesde']
    fechaHasta = request.session['fechaHasta']
    codigoRemoto = request.session['codigoRemoto']
    tit = request.session['titulo']

    return render_to_response('reportesVendedor/vendedorxHora.html', {'fechaDesde': fechaDesde,
                                                                      'fechaHasta': fechaHasta,
                                                                      'codigoRemoto': codigoRemoto, 'tit': tit},
                              context_instance=RequestContext(request))


@login_required
def ventasVendedorPorFormaPago(request):
    if request.session['listaBrutaParaVendedores'] != 0:
        listaBrutaAuxiliar = request.session['listaBrutaParaVendedores']
        listaBruta = []
        if listaBrutaAuxiliar != []:
            for data in listaBrutaAuxiliar:
                if data['RecargoColor'] == None:
                    data['RecargoColor'] = 0

                if data['RecargoLogo'] == None:
                    data['RecargoLogo'] = 0

                valorAnuncio = data['ValorAnuncio']
                if data['SupSaCh'] == 109:
                    valorAnuncio = data['ValorAnuncio'] - data['RecargoColor']

                descManual = 0
                if data['DescuentoAMano'] < 0:
                    descManual = ((valorAnuncio + data['RecargoColor'] + data['RecargoLogo']) -
                                  (data['DescPromocion'] + data['DescConvenio'] + data['DescAgencia'])) * data[
                                     'DescuentoAMano'] * (-1) / 100

                totalRecargo = data['RecargoColor'] + data['RecargoLogo'] + descManual

                totalBruto = valorAnuncio + totalRecargo

                descCms = 0
                if totalBruto != 0:
                    descCms = math.ceil((round((data['DescPromocion'] / totalBruto), 2)) * data['centimetros'])

                # else:
                # cmsNeto = 0

                cmsNeto = data['centimetros'] - descCms

                descAMano = 0
                if data['DescuentoAMano'] > 0:
                    descAMano = ((((valorAnuncio + data['RecargoColor'] + data['RecargoLogo'] + descManual) -
                                   (data['DescPromocion'] + data['DescConvenio'] + data['DescAgencia'])) *
                                  data['DescuentoAMano']) / 100)

                totalDescuento = data['DescPromocion'] + data['DescConvenio'] + descAMano + data['DescAgencia']

                netoSinIva = totalBruto - totalDescuento
                dictionary = dict(NetoSinIva=netoSinIva, CmsNeto=cmsNeto,  #Codigo=data['Codigo'],
                                  formaDePago=data['formaDePago'],
                                  nombreVendedor=data['nombreVendedor'])
                listaBruta.append(dictionary)

        listaCuentaCorriente = []
        listaCuentaCorrienteAux = []
        listaEfectivo = []
        listaEfectivoAux = []
        listaCortesias = []
        listaCortesiasAux = []
        listaCompensacion = []
        listaCompensacionAux = []
        listaReposicion = []
        listaReposicionAux = []

        for elto in listaBruta:
            if elto['formaDePago'] == 1:
                listaEfectivo.append(elto)
            elif elto['formaDePago'] == 4:
                listaCuentaCorriente.append(elto)
            elif elto['formaDePago'] == 6:
                listaCompensacion.append(elto)
            elif elto['formaDePago'] == 7:
                listaCortesias.append(elto)
            elif elto['formaDePago'] == 8:
                listaReposicion.append(elto)


        # listaPorVendedor = []
        Total_CmsNeto = 0
        Total_NetoSinIva = 0

        """ Total por vendendor por Efectivo """
        listaOrdenada = sorted(listaEfectivo, key=operator.itemgetter('nombreVendedor'))
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['nombreVendedor']):
            CmsNeto = sum(item['CmsNeto'] for item in val)
            Total_CmsNeto += CmsNeto
            # aca creo la lista por primera vez con los N tipo de avisos que existen
            listaEfectivoAux.append({'nombreVendedor': key, 'CmsNeto': CmsNeto})

        i = 0
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['nombreVendedor']):
            NetoSinIva = sum(item['NetoSinIva'] for item in val)
            Total_NetoSinIva += NetoSinIva
            listaEfectivoAux[i].update({'NetoSinIva': NetoSinIva})
            i += 1

        listaEfectivoAux = sorted(listaEfectivoAux, key=lambda k: k['CmsNeto'], reverse=True)

        total_porcentajeNetoSinIva = 0
        total_porcentajeCmsNeto = 0

        for data in listaEfectivoAux:

            porcentajeNetoSinIva = 0
            if Total_NetoSinIva != 0:
                porcentajeNetoSinIva = (data['NetoSinIva'] / Total_NetoSinIva) * 100
                total_porcentajeNetoSinIva += porcentajeNetoSinIva

            porcentajeCmsNeto = 0
            if Total_CmsNeto != 0:
                porcentajeCmsNeto = (data['CmsNeto'] / Total_CmsNeto) * 100
                total_porcentajeCmsNeto += porcentajeCmsNeto

            data.update({'PorcentajeNetoSinIva': porcentajeNetoSinIva})
            data.update({'PorcentajeCmsNeto': porcentajeCmsNeto})
            data.update({'FormaDePago': 'Contado'})

        total_efectivoNetoSinIva = Total_NetoSinIva
        total_efectivoCms = Total_CmsNeto

        # listaEfectivoAux.append({'nombreVendedor': '', 'CmsNeto': '', 'NetoSinIva': '','PorcentajeCmsNeto':'', 'PorcentajeNetoSinIva': '', 'FormaDePago':''})

        listaEfectivoAux.append(
            {'nombreVendedor': 'Total Contado', 'CmsNeto': Total_CmsNeto, 'NetoSinIva': Total_NetoSinIva,
             'PorcentajeCmsNeto': total_porcentajeCmsNeto,

             'PorcentajeNetoSinIva': total_porcentajeNetoSinIva, 'FormaDePago': ''})

        listaEfectivoAux.append(
            {'nombreVendedor': '', 'CmsNeto': '', 'NetoSinIva': '', 'PorcentajeCmsNeto': '', 'PorcentajeNetoSinIva': '',
             'FormaDePago': ''})
        """ Los diccionarios vacíos son para colocar divisiones en el GRID y que la información no esté toda junta """
        listaEfectivo = json.dumps(listaEfectivoAux, cls=DjangoJSONEncoder)

        """ Total por vendendor por Cuenta Corriente """
        listaOrdenada = sorted(listaCuentaCorriente, key=operator.itemgetter('nombreVendedor'))
        Total_CmsNeto = 0
        Total_NetoSinIva = 0
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['nombreVendedor']):
            CmsNeto = sum(item['CmsNeto'] for item in val)
            Total_CmsNeto += CmsNeto
            # aca creo la lista por primera vez con los N tipo de avisos que existen
            listaCuentaCorrienteAux.append({'nombreVendedor': key, 'CmsNeto': CmsNeto})

        i = 0
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['nombreVendedor']):
            NetoSinIva = sum(item['NetoSinIva'] for item in val)
            Total_NetoSinIva += NetoSinIva
            listaCuentaCorrienteAux[i].update({'NetoSinIva': NetoSinIva})
            i += 1

        listaCuentaCorrienteAux = sorted(listaCuentaCorrienteAux, key=lambda k: k['CmsNeto'], reverse=True)

        total_porcentajeNetoSinIva = 0
        total_porcentajeCmsNeto = 0

        for data in listaCuentaCorrienteAux:

            porcentajeNetoSinIva = 0
            if Total_NetoSinIva != 0:
                porcentajeNetoSinIva = (data['NetoSinIva'] / Total_NetoSinIva) * 100
                total_porcentajeNetoSinIva += porcentajeNetoSinIva

            porcentajeCmsNeto = 0
            if Total_CmsNeto != 0:
                porcentajeCmsNeto = (data['CmsNeto'] / Total_CmsNeto) * 100
                total_porcentajeCmsNeto += porcentajeCmsNeto

            data.update({'PorcentajeNetoSinIva': porcentajeNetoSinIva})
            data.update({'PorcentajeCmsNeto': porcentajeCmsNeto})
            data.update({'FormaDePago': 'Cuenta Corriente'})

        total_cuentaCorrienteNetoSinIva = Total_NetoSinIva
        total_cuentaCorrienteCms = Total_CmsNeto

        # listaCuentaCorrienteAux.append({'nombreVendedor': '', 'CmsNeto': '', 'NetoSinIva': '', 'PorcentajeCmsNeto':'', 'PorcentajeNetoSinIva': '', 'FormaDePago':''})

        listaCuentaCorrienteAux.append(
            {'nombreVendedor': 'Total Cuenta Corriente', 'CmsNeto': Total_CmsNeto, 'NetoSinIva': Total_NetoSinIva,
             'PorcentajeCmsNeto': total_porcentajeCmsNeto,

             'PorcentajeNetoSinIva': total_porcentajeNetoSinIva, 'FormaDePago': ''})
        listaCuentaCorrienteAux.append(
            {'nombreVendedor': '', 'CmsNeto': '', 'NetoSinIva': '', 'PorcentajeCmsNeto': '', 'PorcentajeNetoSinIva': '',
             'FormaDePago': ''})
        listaCuentaCorriente = json.dumps(listaCuentaCorrienteAux, cls=DjangoJSONEncoder)

        """ Total por vendendor por Compensacion """
        Total_CmsNeto = 0
        Total_NetoSinIva = 0
        listaOrdenada = sorted(listaCompensacion, key=operator.itemgetter('nombreVendedor'))
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['nombreVendedor']):
            CmsNeto = sum(item['CmsNeto'] for item in val)
            Total_CmsNeto += CmsNeto
            # aca creo la lista por primera vez con los N tipo de avisos que existen
            listaCompensacionAux.append({'nombreVendedor': key, 'CmsNeto': CmsNeto})

        i = 0
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['nombreVendedor']):
            NetoSinIva = sum(item['NetoSinIva'] for item in val)
            Total_NetoSinIva += NetoSinIva
            listaCompensacionAux[i].update({'NetoSinIva': NetoSinIva})
            i += 1

        listaCompensacionAux = sorted(listaCompensacionAux, key=lambda k: k['CmsNeto'], reverse=True)

        total_porcentajeNetoSinIva = 0
        total_porcentajeCmsNeto = 0

        for data in listaCompensacionAux:

            porcentajeNetoSinIva = 0
            if Total_NetoSinIva != 0:
                porcentajeNetoSinIva = (data['NetoSinIva'] / Total_NetoSinIva) * 100
                total_porcentajeNetoSinIva += porcentajeNetoSinIva

            porcentajeCmsNeto = 0
            if Total_CmsNeto != 0:
                porcentajeCmsNeto = (data['CmsNeto'] / Total_CmsNeto) * 100
                total_porcentajeCmsNeto += porcentajeCmsNeto

            data.update({'PorcentajeNetoSinIva': porcentajeNetoSinIva})
            data.update({'PorcentajeCmsNeto': porcentajeCmsNeto})
            data.update({'FormaDePago': 'Compensacion'})

        total_compensacionNetoSinIva = Total_NetoSinIva
        total_compensacionCms = Total_CmsNeto

        # listaCompensacionAux.append({'nombreVendedor': '', 'CmsNeto': '', 'NetoSinIva': '', 'PorcentajeCmsNeto':'', 'PorcentajeNetoSinIva': '', 'FormaDePago':''})

        listaCompensacionAux.append(
            {'nombreVendedor': 'Total Compensacion', 'CmsNeto': Total_CmsNeto, 'NetoSinIva': Total_NetoSinIva,
             'PorcentajeCmsNeto': total_porcentajeCmsNeto,

             'PorcentajeNetoSinIva': total_porcentajeNetoSinIva, 'FormaDePago': ''})

        listaCompensacionAux.append(
            {'nombreVendedor': '', 'CmsNeto': '', 'NetoSinIva': '', 'PorcentajeCmsNeto': '', 'PorcentajeNetoSinIva': '',
             'FormaDePago': ''})

        listaCompensacion = json.dumps(listaCompensacionAux, cls=DjangoJSONEncoder)

        """ Total por vendendor por Cortesias """
        Total_CmsNeto = 0
        Total_NetoSinIva = 0
        listaOrdenada = sorted(listaCortesias, key=operator.itemgetter('nombreVendedor'))
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['nombreVendedor']):
            CmsNeto = sum(item['CmsNeto'] for item in val)
            Total_CmsNeto += CmsNeto
            # aca creo la lista por primera vez con los N tipo de avisos que existen
            listaCortesiasAux.append({'nombreVendedor': key, 'CmsNeto': CmsNeto})

        i = 0
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['nombreVendedor']):
            NetoSinIva = sum(item['NetoSinIva'] for item in val)
            Total_NetoSinIva += NetoSinIva
            listaCortesiasAux[i].update({'NetoSinIva': NetoSinIva})
            i += 1

        listaCortesiasAux = sorted(listaCortesiasAux, key=lambda k: k['CmsNeto'], reverse=True)

        total_porcentajeNetoSinIva = 0
        total_porcentajeCmsNeto = 0

        for data in listaCortesiasAux:

            porcentajeNetoSinIva = 0
            if Total_NetoSinIva != 0:
                porcentajeNetoSinIva = (data['NetoSinIva'] / Total_NetoSinIva) * 100
                total_porcentajeNetoSinIva += porcentajeNetoSinIva

            porcentajeCmsNeto = 0
            if Total_CmsNeto != 0:
                porcentajeCmsNeto = (data['CmsNeto'] / Total_CmsNeto) * 100
                total_porcentajeCmsNeto += porcentajeCmsNeto

            data.update({'PorcentajeNetoSinIva': porcentajeNetoSinIva})
            data.update({'PorcentajeCmsNeto': porcentajeCmsNeto})
            data.update({'FormaDePago': 'Cortesias'})

        total_CortesiasNetoSinIva = Total_NetoSinIva
        total_CortesiasCms = Total_CmsNeto

        # listaCortesiasAux.append({'nombreVendedor': '', 'CmsNeto': '', 'NetoSinIva': '', 'PorcentajeCmsNeto':'', 'PorcentajeNetoSinIva': '', 'FormaDePago':''})

        listaCortesiasAux.append(
            {'nombreVendedor': 'Total Cortesias', 'CmsNeto': Total_CmsNeto, 'NetoSinIva': Total_NetoSinIva,
             'PorcentajeCmsNeto': total_porcentajeCmsNeto,

             'PorcentajeNetoSinIva': total_porcentajeNetoSinIva, 'FormaDePago': ''})
        listaCortesiasAux.append(
            {'nombreVendedor': '', 'CmsNeto': '', 'NetoSinIva': '', 'PorcentajeCmsNeto': '', 'PorcentajeNetoSinIva': '',
             'FormaDePago': ''})

        listaCortesias = json.dumps(listaCortesiasAux, cls=DjangoJSONEncoder)

        """ Total por vendendor por Reposicion """
        Total_CmsNeto = 0
        Total_NetoSinIva = 0
        listaOrdenada = sorted(listaReposicion, key=operator.itemgetter('nombreVendedor'))
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['nombreVendedor']):
            CmsNeto = sum(item['CmsNeto'] for item in val)
            Total_CmsNeto += CmsNeto
            # aca creo la lista por primera vez con los N tipo de avisos que existen
            listaReposicionAux.append({'nombreVendedor': key, 'CmsNeto': CmsNeto})

        i = 0
        for key, val in itertools.groupby(listaOrdenada, lambda v: v['nombreVendedor']):
            NetoSinIva = sum(item['NetoSinIva'] for item in val)
            Total_NetoSinIva += NetoSinIva
            listaReposicionAux[i].update({'NetoSinIva': NetoSinIva})
            i += 1

        listaReposicionAux = sorted(listaReposicionAux, key=lambda k: k['CmsNeto'], reverse=True)

        total_porcentajeNetoSinIva = 0
        total_porcentajeCmsNeto = 0

        for data in listaReposicionAux:

            porcentajeNetoSinIva = 0
            if Total_NetoSinIva != 0:
                porcentajeNetoSinIva = (data['NetoSinIva'] / Total_NetoSinIva) * 100
                total_porcentajeNetoSinIva += porcentajeNetoSinIva

            porcentajeCmsNeto = 0
            if Total_CmsNeto != 0:
                porcentajeCmsNeto = (data['CmsNeto'] / Total_CmsNeto) * 100
                total_porcentajeCmsNeto += porcentajeCmsNeto

            data.update({'PorcentajeNetoSinIva': porcentajeNetoSinIva})
            data.update({'PorcentajeCmsNeto': porcentajeCmsNeto})
            data.update({'FormaDePago': 'Reposicion'})

        total_ReposicionNetoSinIva = Total_NetoSinIva
        total_ReposicionCms = Total_CmsNeto

        # listaReposicionAux.append({'nombreVendedor': '', 'CmsNeto': '', 'NetoSinIva': '', 'PorcentajeCmsNeto':'', 'PorcentajeNetoSinIva': '', 'FormaDePago':''})

        listaReposicionAux.append(
            {'nombreVendedor': 'Total Reposicion', 'CmsNeto': Total_CmsNeto, 'NetoSinIva': Total_NetoSinIva,
             'PorcentajeCmsNeto': '',

             'PorcentajeNetoSinIva': total_porcentajeNetoSinIva, 'FormaDePago': ''})

        totalNetoGeneral = total_efectivoNetoSinIva + total_cuentaCorrienteNetoSinIva + total_compensacionNetoSinIva + total_ReposicionNetoSinIva + total_CortesiasNetoSinIva
        totalCmsGeneral = total_efectivoCms + total_cuentaCorrienteCms + total_compensacionCms + total_ReposicionCms + total_CortesiasCms

        listaReposicionAux.append(
            {'nombreVendedor': '', 'CmsNeto': '', 'NetoSinIva': '', 'PorcentajeCmsNeto': '', 'PorcentajeNetoSinIva': '',
             'FormaDePago': ''})

        listaReposicionAux.append(
            {'nombreVendedor': 'Total General', 'CmsNeto': totalCmsGeneral, 'NetoSinIva': totalNetoGeneral,
             'PorcentajeCmsNeto': '',

             'PorcentajeNetoSinIva': '', 'FormaDePago': ''})

        listaReposicion = json.dumps(listaReposicionAux, cls=DjangoJSONEncoder)


        # ------------------------Variables y procesamiento para el excel -----------------------------------------
        listaData = []
        for data in listaEfectivoAux:
            listaData.append(data)
        for data in listaCuentaCorrienteAux:
            listaData.append(data)
        for data in listaCompensacionAux:
            listaData.append(data)
        for data in listaCortesiasAux:
            listaData.append(data)
        for data in listaReposicionAux:
            listaData.append(data)

        request.session['data'] = listaData
        #

        request.session['headers'] = ['Vendedor', 'Cms Neto', 'Neto Sin Iva', '% Cms Neto', '% Neto Sin Iva',
                                      'Forma de Pago']
        #
        request.session['titulo'] = 'Resumen de Ventas por Vendedor por Forma de Pago'
        #
        request.session['keys'] = ['nombreVendedor', 'CmsNeto', 'NetoSinIva', 'PorcentajeCmsNeto',
                                   'PorcentajeNetoSinIva', 'FormaDePago']





        #-------------------------------------------------------------------------------------------------------

        codRemoto = request.session['codigoRemoto']
        fechaDesde = request.session['fechaDesde']
        fechaHasta = request.session['fechaHasta']

        return render_to_response('reportesVendedor/ventasVendedorPorFormaPago.html',
                                  {'listaReposicion': listaReposicion,
                                   'listaCortesias': listaCortesias,
                                   'listaCuentaCorriente': listaCuentaCorriente,
                                   'listaCompensacion': listaCompensacion, 'listaEfectivo': listaEfectivo,
                                   'tit': 'Ventas por Vendedor por Forma de Pago',
                                   'codRemoto': codRemoto, 'fechaDesde': fechaDesde, 'fechaHasta': fechaHasta},
                                  context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect('/reportesVendedor/formVentasVendedor')


@login_required
def formAvisosPublicadosFacturados(request):
    if request.method == 'POST':
        formulario = formPromociones(request.POST)

        if formulario.is_valid():

            cursor = connections['SDCLASS'].cursor()
            fechaDesde = formulario.cleaned_data['fechaDesde']
            df = DateFormat(fechaDesde)
            fechaDesde = df.format('Y-d-m')

            fechaDesdeModoLatino = df.format('d/m/Y')

            fechaHasta = formulario.cleaned_data['fechaHasta']
            df = DateFormat(formulario.cleaned_data['fechaHasta'] + timedelta(days=1))
            fechaHasta = df.format('Y-d-m')

            df = DateFormat(formulario.cleaned_data['fechaHasta'])
            fechaHastaModoLatino = df.format('d/m/Y')

            request.session['fechaDesde'] = fechaDesdeModoLatino
            request.session['fechaHasta'] = fechaHastaModoLatino

            cursor.execute("SELECT * FROM AvisosQuesefacturanNadia(%s, %s)", (fechaDesde, fechaHasta))

            listaAux = dictfetchall(cursor)

            avisosQueSeFacturanYSePublican = []
            avisosQueSeFacturanYNoSePublican = []
            for data in listaAux:
                importeSinImpuestoPorDia = 0
                if data['ImporteBruto'] != 0:
                    porcentXDia = (data['PrecioXDia2'] * 100) / data['ImporteBruto']
                    descuentosYRecargosXAviso = data['DescuentoaMano'] + data['Descuentos'] + data['RecargoColor'] + \
                                                data['RecargoLogo']
                    descuentosYRecargosXDia = (porcentXDia * descuentosYRecargosXAviso) / 100

                    importeSinImpuestoPorDia = descuentosYRecargosXDia + data['PrecioXDia2']

                data.update({'importeSinImpuestoPorDia': importeSinImpuestoPorDia})

                fechaquepublica = data['FechaQuePublica'].strftime("%Y-%m-%d")

                fechaquepublica = datetime.strptime(fechaquepublica, '%Y-%m-%d')
                fechaDesde1 = datetime.strptime(fechaDesde, '%Y-%d-%m')
                fechaHasta1 = datetime.strptime(fechaHasta, '%Y-%d-%m')

                if fechaquepublica < fechaDesde1 or fechaquepublica > fechaHasta1:
                    avisosQueSeFacturanYNoSePublican.append(data)
                else:
                    avisosQueSeFacturanYSePublican.append(data)

            totalSinImpuestosAvisosQueSeFacturanYNoSePublican = 0
            for data in avisosQueSeFacturanYNoSePublican:
                totalSinImpuestosAvisosQueSeFacturanYNoSePublican += data['importeSinImpuestoPorDia']

            totalSinImpuestosAvisosQueSeFacturanYSePublican = 0
            for data in avisosQueSeFacturanYSePublican:
                totalSinImpuestosAvisosQueSeFacturanYSePublican += data['importeSinImpuestoPorDia']

            listaAux = []
            listaAux.append(dict(concepto='Avisos que se Facturan y se Publican',
                                 total=totalSinImpuestosAvisosQueSeFacturanYSePublican))
            listaAux.append(dict(concepto='Avisos que se Facturan y NO se Publican *',
                                 total=totalSinImpuestosAvisosQueSeFacturanYNoSePublican))

            listaAux.append(dict(concepto='', total=0))
            listaAux.append(dict(concepto='Total',
                                 total=totalSinImpuestosAvisosQueSeFacturanYNoSePublican + totalSinImpuestosAvisosQueSeFacturanYSePublican))

            request.session['lista_resultados'] = listaAux

            request.session['titulo'] = 'Avisos Facturados y Publicados'
            request.session['fechaDesde'] = fechaDesdeModoLatino
            request.session['fechaHasta'] = fechaHastaModoLatino

            ############### Variables para el Excel ####################
            request.session['data'] = avisosQueSeFacturanYSePublican + avisosQueSeFacturanYNoSePublican

            request.session['keys'] = ['CodigoAviso', 'FechaAviso', 'FechaPublicacion', 'Nodo', 'Referencia', 'Alto',
                                       'Ancho', 'TotalCm',
                                       'Tarifa', 'ImporteBruto', 'DescuentoaMano', 'Descuentos', 'RecargoColor',
                                       'RecargoLogo',
                                       'ImporteSinImpuestos', 'NroPedido', 'TipoComprobante', 'Letra', 'NroFactura',
                                       'CondicionVenta',
                                       'TotalFacturaSinImpuestos', 'FechaQuePublica', 'PrecioXDia2',
                                       'importeSinImpuestoPorDia']

            request.session['headers'] = ['Cod Aviso', 'Fecha Aviso', 'Fecha Publicacion', 'Nodo', 'Referencia', 'Alto',
                                          'Ancho', 'Total Cms',
                                          'Tarifa', 'Importe Bruto', 'Descuento a Mano', 'Descuentos', 'Recargo Color',
                                          'Recargo Logo',
                                          'Importe sin Impuestos', 'Nro Pedido', 'Tipo Comprobante', 'Letra',
                                          'Nro Factura', 'Condicion Venta',
                                          'Total Factura sin Impuestos', 'Fecha que Publica', 'Precio x Dia',
                                          'Imp Sin Impuesto Por Dia']

            listaGrafico = []
            porcAvisosNoPub, porcAvisosPub = 0, 0
            if totalSinImpuestosAvisosQueSeFacturanYNoSePublican + totalSinImpuestosAvisosQueSeFacturanYSePublican != 0:
                porcAvisosNoPub = (totalSinImpuestosAvisosQueSeFacturanYNoSePublican * 100) / (
                    totalSinImpuestosAvisosQueSeFacturanYNoSePublican + totalSinImpuestosAvisosQueSeFacturanYSePublican)
                porcAvisosPub = (totalSinImpuestosAvisosQueSeFacturanYSePublican * 100) / (
                    totalSinImpuestosAvisosQueSeFacturanYNoSePublican + totalSinImpuestosAvisosQueSeFacturanYSePublican)

            listaGrafico.append(dict(nombre='Avisos Facturados y No Publicados', porc=porcAvisosNoPub))
            listaGrafico.append(dict(nombre='Avisos Facturados y Publicados', porc=porcAvisosPub))

            listaGrafico = json.dumps(listaGrafico, cls=DjangoJSONEncoder)

            return render_to_response('reportesFacturas/facturasPublicadas/AvisosFacturadosYPublicados.html',
                                      {'tit': 'Avisos Facturados y Publicados',
                                       'fechaDesde': fechaDesdeModoLatino,
                                       'fechaHasta': fechaHastaModoLatino,
                                       'listaGrafico': listaGrafico},
                                      context_instance=RequestContext(request))
    else:
        formulario = formPromociones()

    return render_to_response('reportesFacturas/facturasPublicadas/formAvisosFacturadosYPublicados.html',
                              {'formulario': formulario},
                              context_instance=RequestContext(request))


def formFacturasMensuales(request):
    if request.method == 'POST':
        formulario = formPromociones(request.POST)

        if formulario.is_valid():

            cursor = connections['SDCLASS'].cursor()
            cursor2 = connections['SDCLASS'].cursor()
            fechaDesde = formulario.cleaned_data['fechaDesde']
            df = DateFormat(fechaDesde)
            fechaDesde = df.format('Y-d-m')

            fechaDesdeModoLatino = df.format('d/m/Y')

            fechaHasta = formulario.cleaned_data['fechaHasta']
            df = DateFormat(fechaHasta)
            fechaHasta = df.format('Y-d-m')
            fechaHastaModoLatino = df.format('d/m/Y')

            df = DateFormat(formulario.cleaned_data['fechaHasta'] + timedelta(days=1))
            fechaHasta = df.format('Y-d-m')
            # print fechaHasta

            request.session['fechaDesde'] = fechaDesdeModoLatino
            request.session['fechaHasta'] = fechaHastaModoLatino

            cursor.execute("select NroAviso,ImporteSinImpuestos,NombreCliente,"  # FechaFactura,
                           "TipoComprobante,NroFactura,CondicionVenta,NroPedido,Letra, Comentario"  #Comentario esta por las refacturas
                           " from viewfacturasSDCLASS where FechaFactura between %s and %s", (fechaDesde, fechaHasta))

            listaSDCLASS = dictfetchall(cursor)

            cursor2.execute("select desc1,NroFactura,TipoComprobante,NombreCliente,"  # FechaFactura,
                            "CondicionVenta,Letra,NroPedido,ImporteSinImpuestos, Comentario"  #
                            " from viewfacturasNOSDCLASS where FechaFactura between %s and %s",
                            (fechaDesde, fechaHasta))

            listaNOSDCLASS = dictfetchall(cursor2)
            # print fechaHasta, fechaDesde, listaNOSDCLASS

            listaAuxiliar = itertools.chain(listaSDCLASS, listaNOSDCLASS)
            listaFinal, lista_resumida = [], []
            total_publicidad, nro_aviso_anterior, total_no_publicidad = 0, 0, 0

            for i in listaAuxiliar:
                if 'NroAviso' in i.keys():
                    if i['NroAviso'] != nro_aviso_anterior:
                        nro_aviso_anterior = i['NroAviso']
                        i['identificador'] = 'Publicidad'
                        i['descripcion'] = i.pop('NroAviso')
                        if i['TipoComprobante'] == 'Nota Credito':
                            total_publicidad = total_publicidad - i['ImporteSinImpuestos']
                        else:
                            total_publicidad = total_publicidad + i['ImporteSinImpuestos']
                    else:

                        nro_aviso_anterior = i['NroAviso']

                if 'desc1' in i.keys():

                    if (i['NombreCliente'] == u'Fideicomiso Adm.de Pautas Pub.ofic') \
                            or (i['NombreCliente'] == u'LOTERIA CHAQUENA') \
                            or (i['NombreCliente'] == u'Ministerio de Justicia de Corrientes') \
                            or (i['NombreCliente'] == u'Relevamientos Catastrales S.A./Ex-SyK') \
                            or (i['NombreCliente'] == u'Municip. de Saenz Pena') \
                            or (i['NombreCliente'] == u'Jef. De Gabinete Minist Sec M.c.'):
                        i['identificador'] = 'Publicidad'
                        i['descripcion'] = i.pop('desc1')
                        if (i['TipoComprobante'] == 'Nota Credito'):
                            total_publicidad = total_publicidad - i['ImporteSinImpuestos']
                        else:
                            total_publicidad = total_publicidad + i['ImporteSinImpuestos']
                    else:
                        i['identificador'] = 'No Publicidad'
                        i['descripcion'] = i.pop('desc1')  #u'desc1'

                        if (i['TipoComprobante'] == 'Nota Credito'):
                            total_no_publicidad = total_no_publicidad - i['ImporteSinImpuestos']
                        else:
                            total_no_publicidad = total_no_publicidad + i['ImporteSinImpuestos']
                #print i.keys
                listaFinal.append(i)

            facturacion_total = total_publicidad + total_no_publicidad
            porcentaje_publicidad = (total_publicidad / facturacion_total) * 100
            porcentaje_no_publicidad = (total_no_publicidad / facturacion_total) * 100

            lista_resumida = [{'FuenteIngreso': 'Publicidad', 'ImportesinImpuestos': total_publicidad},
                              {'FuenteIngreso': 'No Publicidad', 'ImportesinImpuestos': total_no_publicidad},
                              {'FuenteIngreso': ' ', 'ImportesinImpuestos': ' '},
                              {'FuenteIngreso': 'Total', 'ImportesinImpuestos': facturacion_total}]
            lista_para_grafico = [{'nombre': 'Publicidad', 'porcentaje': porcentaje_publicidad},
                                  {'nombre': 'No Publicidad', 'porcentaje': porcentaje_no_publicidad}]
            tit = 'Facturas de Publicidad y No Publicidad'

            #########   Variables para Excel    ################################
            request.session['data'] = listaFinal

            request.session['keys'] = ["NroPedido", "NroFactura", "Letra", "NombreCliente", "CondicionVenta",
                                       "identificador", "ImporteSinImpuestos", "descripcion", "Comentario",
                                       "TipoComprobante"]

            request.session['headers'] = ["Nro Pedido", "Nro Factura", "Letra", "Nombre Cliente", "CondicionVenta",
                                          "Identificador", "Importe sin Impuestos", "Descripcion", "Comentario",
                                          "Tipo Comprobante"]

            request.session['titulo'] = tit
            #########################################################

            lista_resumida = json.dumps(lista_resumida, cls=DjangoJSONEncoder)
            return render_to_response('reportesFacturas/facturasTotales/facturasMensuales.html',
                                      {'fechaDesde': fechaDesdeModoLatino, 'tit': tit,
                                       'listaFacturacion': lista_resumida,
                                       'fechaHasta': fechaHastaModoLatino, 'listaGrafico': lista_para_grafico},
                                      context_instance=RequestContext(request))

    else:
        formulario = formPromociones()

    return render_to_response('reportesFacturas/facturasTotales/formFacturasMensuales.html', {'formulario': formulario},
                              context_instance=RequestContext(request))


@user_passes_test(grupo_check)
def formCapturadoresIva(request):
    if request.method == 'POST':
        formulario = formVentasCaptura(request.POST)

        if formulario.is_valid():

            cursor = connections['sqlserver2008'].cursor()

            codRemoto = formulario.cleaned_data['codRemoto']
            if codRemoto == u'1':
                request.session['codigoRemoto'] = 'Chaco'

            else:
                request.session['codigoRemoto'] = 'Corrientes'
            codigoremoto = request.session['codigoRemoto']

            dia = formulario.cleaned_data['hoy']
            if dia == u'1':
                fechaDesde = time.strftime('%Y-%d-%m')
                # facu aca hay que obtener el día de hoy y sumarle uno, lo mismo para fechaHasta si ingresa con uiquery.
                fechaHasta = time.strftime('%Y-%d-%m')
                fechaDesdeModoLatino = time.strftime('%d/%m/%Y')
                fechaHastaModoLatino = fechaDesdeModoLatino
            else:
                fechaDesde = formulario.cleaned_data['fechaDesde']
                df = DateFormat(fechaDesde)
                fechaDesde = df.format('Y-d-m')

                fechaDesdeModoLatino = df.format('d/m/Y')

                fechaHasta = formulario.cleaned_data['fechaHasta']
                df = DateFormat(fechaHasta)
                fechaHasta = df.format('Y-d-m')
                fechaHastaModoLatino = df.format('d/m/Y')

                df = DateFormat(formulario.cleaned_data['fechaHasta'])
                fechaHasta = df.format('Y-d-m')
                # print fechaHasta

            request.session['fechaDesde'] = fechaDesdeModoLatino
            request.session['fechaHasta'] = fechaHastaModoLatino

            cursor.execute("select * from EstadisticasAvisosConTasaIVA(%s,%s,%s)", (fechaDesde, fechaHasta, codRemoto))
            listaBruta = dictfetchall(cursor)

            listaIvaIncorrecto, listaIva = [], []
            for data in listaBruta:
                data['nombre'] = data['nombre'].replace(' ','')
                if data['TasaIVA'] == 10.5 or data['TasaIVA'] == 21.0:
                    data.update({'verifica': 'Correctos'})
                    listaIva.append(data)
                else:
                    data.update({'verifica': 'Incorrectos'})
                    listaIvaIncorrecto.append(data)

            tit = 'Control Tasa de IVA de Avisos'
            request.session['data'] = listaIva + listaIvaIncorrecto
            request.session['titulo'] = tit

            print request.session['data']

            # lista_resumida = json.dumps(lista_resumida, cls=DjangoJSONEncoder)
            return render_to_response('CapturadoresIva/capturadoresIVA.html', {'tit': tit,
                                                                               'fechaDesde': fechaDesdeModoLatino,
                                                                               'fechaHasta': fechaHastaModoLatino,
                                                                               'codigoRemoto': codigoremoto},
                                      context_instance=RequestContext(request))

    else:
        formulario = formVentasCaptura()

    return render_to_response('capturadoresIva/formAvisosConTasaIva.html', {'formulario': formulario},
                              context_instance=RequestContext(request))