import user
from django.conf.urls import patterns, include, url

from django.contrib import admin
from aplicacion.views import json_test, json_testA, json_testGrupo, json_totales, menuReportesEstadisticos, inicio,  \
    json_ventasNetasAnuales, json_graficostotales, detalleRecargosyDescuentos, detalleCmsVendidosyCedidos, enviarCorreoAjax, \
    json_graficosFormasDePagoPorCms, viewFormPromociones, promociones, jsonPromociones, json_GrupoPromociones, \
    viewFormVentasCaptura, capturaDiayHora, listaDiayHora, jsonTotalVendedorxHora, \
    listaVentasPorVendedor, formVentasVendedor, ventasVendedorPorHora, ajaxVendedorHoraFormasDePago, \
    jsonTotalVendedorxHoraAjax, ventasVendedorPorFormaPago, json_AvisosFacturadosYPublicados, formAvisosPublicadosFacturados, \
    formFacturasMensuales, formCapturadoresIva

admin.autodiscover()

urlpatterns = patterns('',

        url(r'^$',inicio),

        url(r'^loginView/','aplicacion.views.loginView'), #, {'template_name':'inicio/index.html'}

        url(r'^reportesFormasDePago/','aplicacion.views.reportesFormasDePago'), #, {'template_name':'inicio/index.html'}

        url(r'^menuReportesEstadisticos/', menuReportesEstadisticos),

        url(r'^errorGeneral', 'aplicacion.views.someError'),

        # Informes de Cta Cte A

        url(r'^listaCtaCteA/','aplicacion.views.listaCtaCteA'), #, {'template_name':'inicio/index.html'}


        url(r'^cuentaCorrienteB/','aplicacion.views.cuentaCorrienteB'),

        url(r'^cuentaCorrienteA/','aplicacion.views.cuentaCorrienteA'),

        url(r'^grupo/','aplicacion.views.grupo'),

        #Informes Mensuales
        url(r'^ventasMensuales/','aplicacion.views.ventasMensuales'),
        url(r'^guardarTotales/','aplicacion.views.guardarTotales'),

        url(r'^detalleRecargosyDescuentos/$', detalleRecargosyDescuentos),
        url(r'^detalleCmsVendidosyCedidos/',detalleCmsVendidosyCedidos),



        #Informes Anuales
        url(r'^formVentaNetaAnual/','aplicacion.views.formVentasNetasAnuales'),


        ###### Reportes de Promociones ##########
        url(r'^promociones/formPromociones',viewFormPromociones),
        url(r'^grupoPromocion',promociones),
        url(r'^listaPromociones/','aplicacion.views.listaPromociones'),

        ### Reportes de Ventas dia y hora

        url(r'^ventasDiayHora/formVentasCaptura',viewFormVentasCaptura),
        url(r'^ventasDiayHora/capturaDiayHora',capturaDiayHora),
        url(r'^ventasDiayHora/listaDiayHora',listaDiayHora),

         ### Reportes Vendedor
        url(r'^reportesVendedor/formVentasVendedor',formVentasVendedor),
        url(r'^reportesVendedor/listaVentasPorVendedor',listaVentasPorVendedor),
        url(r'^reportesVendedor/ventasVendedorPorHora',ventasVendedorPorHora),
        url(r'^reportesVendedor/ventasVendedorPorFormaPago',ventasVendedorPorFormaPago),
        url(r'^reportesVendedor/ajaxVendedorPorHoraFormasDePago/',ajaxVendedorHoraFormasDePago),

        ### reportesFacturas
        url(r'^reportesFacturas/facturasPublicadas/formAvisosPublicadosFacturados/',formAvisosPublicadosFacturados),
        url(r'^reportesFacturas/facturasTotales/formFacturasMensuales/',formFacturasMensuales),

        ## ReportesCapturadoresIva
        url(r'^capturadoresIva/formFacturasMensuales/',formCapturadoresIva),

        #Reportes Excel y PDF
        url(r'^exportarAPdf/', 'aplicacion.views.view_in_pdf', name='templatePdf2'),
        url(r'^exportarAXls/', ('aplicacion.views.viewToXls')),

        #Para cargar Grids
        url(r'^verCCB/$', json_test),
        url(r'^verCCA/$', json_testA),
        url(r'^verCCAGrupo/$', json_testGrupo),
        url(r'^verTotales/$', json_totales),
        url(r'^json_ventasNetasAnuales/$', json_ventasNetasAnuales),
        url(r'^json_graficosTotales/$', json_graficostotales),
        url(r'^json_graficosFormasDePagoPorCms/$', json_graficosFormasDePagoPorCms),
        url(r'^jsonPromociones/$', jsonPromociones),
        url(r'^json_GrupoPromociones/$', json_GrupoPromociones),
        url(r'^jsonTotalVendedorxHora/$', jsonTotalVendedorxHora),
        url(r'^jsonTotalVendedorxHoraAjax/$', jsonTotalVendedorxHoraAjax),
        url(r'^json_AvisosFacturadosYPublicados/$', json_AvisosFacturadosYPublicados),





        #Correo
        url(r'^enviarCorreoAjax$', enviarCorreoAjax),




        url(r'^salir/','aplicacion.views.logoutView'),
        url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
        url(r'^admin/', include(admin.site.urls)),
)
