
 //$(document).ready(function(){

    jQuery("#list").jqGrid({
    url:'/json_graficosFormasDePagoPorCms',
    datatype: 'json',
    mtype: 'GET',


    colNames:['Forma de Pago','Centimetros'],

    colModel :[
      {name:'nombre',index:'nombre', width:350, editable:true, classes: 'clasepropia',
          cellattr: function (rowId, tv, rawObject, cm, rdata) {
            console.log(rawObject);
                if (rawObject.nombre == 'Compensacion') {
                    return ' onclick="mostrarGraficoCompensacion()" style="color:blue; cursor: pointer;"';
                }
                if (rawObject.nombre == 'CuentaCorriente') {
                    return ' onclick="mostrarGrafico()" style="color:blue; cursor: pointer;"';
                }
                if (rawObject.nombre == 'Efectivo') {
                    return ' onclick="mostrarGraficoContado()" style="color:blue; cursor: pointer;"';
                }
                if (rawObject.nombre == 'Cortesias') {
                    return ' onclick="mostrarGraficoCortesias()" style="color:blue; cursor: pointer;"';
                }
                if (rawObject.nombre == 'Reposicion') {
                    return ' onclick="mostrarGraficoReposicion()" style="color:blue; cursor: pointer;"';
                }
                if (rawObject.nombre == 'OtrasFormasDePago') {
                    return ' onclick="mostrarGraficoOtrasFormasDePago()" style="color:blue; cursor: pointer;"';
                }
            }
    },
      {name:'cms',index:'cms',width:200,align:"right",sorttype:'number',formatter: currencyFmatter2,summaryType:'sum'}

    ],

    rowNum:-1,
    //rownumbers: true,
    viewrecords: true,
    emptyrecords : "No hay registros para mostrar",
    height: 'auto',
    sortorder: 'desc',
    viewrecords: true,

    //pager: $('#gridpager'),
    //footerrow: true,

    //loadOnce: true,
    caption: 'Recargos y Descuentos en Anuncios'
    //emptyDataText:'No hay registros'


  });


function currencyFmatter2 (cellvalue, options, rowObject)
{
   if (cellvalue == 0) {
        return '';
   }else {
       return parseFloat(Math.round(cellvalue * 100) / 100).toFixed(2);
   }


}


jQuery("#list").jqGrid('navGrid','#list',{add:false,edit:false,del:false});

//});

function mostrarGrafico(){

    if ($('#graficoCuentaCorriente').is(':visible')){
        $('#graficoCuentaCorriente').hide('slow');
    }else{
        $('#graficoCuentaCorriente').show('slow');

    }
}

function mostrarGraficoContado(){

    if ($('#graficoContado').is(':visible')){
        $('#graficoContado').hide('slow');
    }else{
        $('#graficoContado').show('slow');

    }
}
function mostrarGraficoCompensacion(){

    if ($('#graficoCompensacion').is(':visible')){
        $('#graficoCompensacion').hide('slow');
    }else{
        $('#graficoCompensacion').show('slow');

    }
}
function mostrarGraficoReposicion(){

    if ($('#graficoReposicion').is(':visible')){
        $('#graficoReposicion').hide('slow');
    }else{
        $('#graficoReposicion').show('slow');

    }
}
function mostrarGraficoCortesias(){

    if ($('#graficoCortesias').is(':visible')){
        $('#graficoCortesias').hide('slow');
    }else{
        $('#graficoCortesias').show('slow');

    }
}
function mostrarGraficoOtrasFormasDePago(){

    if ($('#graficoOtrasFormasDePago').is(':visible')){
        $('#graficoOtrasFormasDePago').hide('slow');
    }else{
        $('#graficoOtrasFormasDePago').show('slow');

    }
}

function mostrarGraficoDesc(){
    if ($('#graficoFormasDePago').is(':visible')){
        $('#graficoFormasDePago').hide('slow');
    }else{
        $('#graficoFormasDePago').show('slow');

    }
}

$(function () {

    var listaTotalCmsPorFormasDePago = {{listaParaGrafico | safe}};
    //console.log(listaTotalCmsPorFormasDePago);


    var dataFormasDePago = [];
    if (listaTotalCmsPorFormasDePago[0].porcCms != 0) {
        dataFormasDePago.push(['Cuenta Corriente', parseFloat(listaTotalCmsPorFormasDePago[0].porcCms)]);
    }
    if (listaTotalCmsPorFormasDePago[1].porcCms != 0) {
        dataFormasDePago.push(['Contado', parseFloat(listaTotalCmsPorFormasDePago[1].porcCms)]);
    }
    if (listaTotalCmsPorFormasDePago[2].porcCms != 0) {
        dataFormasDePago.push(['Reposicion', parseFloat(listaTotalCmsPorFormasDePago[2].porcCms)]);
    }
    if (listaTotalCmsPorFormasDePago[3].porcCms != 0) {
        dataFormasDePago.push(['Compensacion', parseFloat(listaTotalCmsPorFormasDePago[3].porcCms)]);
    }
    if (listaTotalCmsPorFormasDePago[4].porcCms != 0) {
        dataFormasDePago.push(['Cortesias', parseFloat(listaTotalCmsPorFormasDePago[4].porcCms)]);
    }
    if (listaTotalCmsPorFormasDePago[5].porcCms != 0) {
        dataFormasDePago.push(['Otras Formas de Pago', parseFloat(listaTotalCmsPorFormasDePago[5].porcCms)]);
    }




    var listaCmsXCuentaCorriente = {{listaCmsXCuentaCorriente | safe}};

    var dataCmsXCuentaCorriente = [];

    for (i=0 ; i < listaCmsXCuentaCorriente.length; i++){
        if (listaCmsXCuentaCorriente[i].porcentaje != 0){
            dataCmsXCuentaCorriente.push([listaCmsXCuentaCorriente[i].aviso.toString(), parseFloat(listaCmsXCuentaCorriente[i].porcentaje)]);
        }
    }

     var listaCmsXContado = {{listaCmsXContado | safe}};

    var dataCmsXContado = [];

    for (i=0 ; i < listaCmsXContado.length; i++){
        if (listaCmsXContado[i].porcentaje != 0){
            dataCmsXContado.push([listaCmsXContado[i].aviso.toString(), parseFloat(listaCmsXContado[i].porcentaje)]);
        }
    }

     var listaCmsXCompensacion = {{listaCmsXCompensacion | safe}};

    var dataCmsXCompensacion = [];

    for (i=0 ; i < listaCmsXCompensacion.length; i++){
        if (listaCmsXCompensacion[i].porcentaje != 0){
            dataCmsXCompensacion.push([listaCmsXCompensacion[i].aviso.toString(), parseFloat(listaCmsXCompensacion[i].porcentaje)]);
        }
    }

     var listaCmsXReposicion = {{listaCmsXReposicion | safe}};

    var dataCmsXReposicion = [];

    for (i=0 ; i < listaCmsXReposicion.length; i++){
        if (listaCmsXReposicion[i].porcentaje != 0){
            dataCmsXReposicion.push([listaCmsXReposicion[i].aviso.toString(), parseFloat(listaCmsXReposicion[i].porcentaje)]);
        }
    }

     var listaCmsXCortesias = {{listaCmsXCortesias | safe}};

    var dataCmsXCortesias = [];

    for (i=0 ; i < listaCmsXCortesias.length; i++){
        if (listaCmsXCortesias[i].porcentaje != 0){
            dataCmsXCortesias.push([listaCmsXCortesias[i].aviso.toString(), parseFloat(listaCmsXCortesias[i].porcentaje)]);
        }
    }

     var listaCmsXOtrasFormasDePago = {{listaCmsXOtrasFormasDePago | safe}};

    var dataCmsXOtrasFormasDePago = [];

    for (i=0 ; i < listaCmsXOtrasFormasDePago.length; i++){
        if (listaCmsXOtrasFormasDePago[i].porcentaje != 0){
            dataCmsXOtrasFormasDePago.push([listaCmsXOtrasFormasDePago[i].aviso.toString(), parseFloat(listaCmsXOtrasFormasDePago[i].porcentaje)]);
        }
    }

    //console.log(dataCmsXCuentaCorriente);

var highchartsOptions = Highcharts.setOptions({
      lang: {
            loading: 'Aguarde...',
            exportButtonTitle: "Exportar",
            printButtonTitle: "Imprimir",
            rangeSelectorFrom: "De",
            rangeSelectorTo: "Hasta",
            rangeSelectorZoom: "Periodo",
            printChart: 'Imprimir Grafico',
            downloadPNG: 'Descargar imagen en PNG',
            downloadJPEG: 'Descargar imagen en JPEG',
            downloadPDF: 'Descargar imagen en PDF',
            downloadSVG: 'Descargar imagen en SVG'

            }
      }
  );
    $('#graficoFormasDePago').highcharts({
        chart: {
            type: 'pie',
            options3d: {
                enabled: true,
                alpha: 45,
                beta: 0
            }
        },
        //options : highchartsOptions,

        title: {
            text: 'Representacion Grafica de Centimetros por Formas de Pago'
        },
        tooltip: {
            pointFormat: '{series.name}: <b>{point.percentage:.1f}%</b>'
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                depth: 35,
                dataLabels: {
                    enabled: true,
                    format: '{point.name}'
                }
            }
        },
        series: [{
            type: 'pie',
            name: 'Porcentaje',
            data: dataFormasDePago
        }]
    });

    //Esta es la parte de los porcentajes de los aviso por forma de pago de Cuenta Corriente
     $('#graficoCuentaCorriente').highcharts({
        chart: {
            type: 'pie',
            options3d: {
                enabled: true,
                alpha: 45,
                beta: 0
            }
        },
        //options : highchartsOptions,

        title: {
            text: 'Representacion Grafica de Centimetros Vendidos en Cuenta Corriente discriminado por Tipo de Aviso'
        },
        tooltip: {
            pointFormat: '{series.name}: <b>{point.percentage:.1f}%</b>'
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                depth: 35,
                dataLabels: {
                    enabled: true,
                    format: '{point.name}'
                }
            }
        },
        series: [{
            type: 'pie',
            name: 'Porcentaje',
            data: dataCmsXCuentaCorriente
        }]
    });


    //Esta es la parte de los porcentajes de los aviso por forma de pago de Contado
    $('#graficoContado').highcharts({
        chart: {
            type: 'pie',
            options3d: {
                enabled: true,
                alpha: 45,
                beta: 0
            }
        },
        //options : highchartsOptions,

        title: {
            text: 'Representacion Grafica de Centimetros Vendidos en Contado discriminado por Tipo de Aviso'
        },
        tooltip: {
            pointFormat: '{series.name}: <b>{point.percentage:.1f}%</b>'
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                depth: 35,
                dataLabels: {
                    enabled: true,
                    format: '{point.name}'
                }
            }
        },
        series: [{
            type: 'pie',
            name: 'Porcentaje',
            data: dataCmsXContado
        }]
    });


    //Esta es la parte de los porcentajes de los aviso por forma de pago de Compensacion
    $('#graficoCompensacion').highcharts({
        chart: {
            type: 'pie',
            options3d: {
                enabled: true,
                alpha: 45,
                beta: 0
            }
        },
        //options : highchartsOptions,

        title: {
            text: 'Representacion Grafica de Centimetros Vendidos en Compensacion discriminado por Tipo de Aviso'
        },
        tooltip: {
            pointFormat: '{series.name}: <b>{point.percentage:.1f}%</b>'
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                depth: 35,
                dataLabels: {
                    enabled: true,
                    format: '{point.name}'
                }
            }
        },
        series: [{
            type: 'pie',
            name: 'Porcentaje',
            data: dataCmsXCompensacion
        }]
    });


    //Esta es la parte de los porcentajes de los aviso por forma de pago de Cortesias
    $('#graficoCortesias').highcharts({
        chart: {
            type: 'pie',
            options3d: {
                enabled: true,
                alpha: 45,
                beta: 0
            }
        },
        //options : highchartsOptions,

        title: {
            text: 'Representacion Grafica de Centimetros Vendidos en Cortesias discriminado por Tipo de Aviso'
        },
        tooltip: {
            pointFormat: '{series.name}: <b>{point.percentage:.1f}%</b>'
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                depth: 35,
                dataLabels: {
                    enabled: true,
                    format: '{point.name}'
                }
            }
        },
        series: [{
            type: 'pie',
            name: 'Porcentaje',
            data: dataCmsXCortesias
        }]
    });


    //Esta es la parte de los porcentajes de los aviso por forma de pago de Reposicion
    $('#graficoReposicion').highcharts({
        chart: {
            type: 'pie',
            options3d: {
                enabled: true,
                alpha: 45,
                beta: 0
            }
        },
        //options : highchartsOptions,

        title: {
            text: 'Representacion Grafica de Centimetros Vendidos en Reposicion discriminado por Tipo de Aviso'
        },
        tooltip: {
            pointFormat: '{series.name}: <b>{point.percentage:.1f}%</b>'
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                depth: 35,
                dataLabels: {
                    enabled: true,
                    format: '{point.name}'
                }
            }
        },
        series: [{
            type: 'pie',
            name: 'Porcentaje',
            data: dataCmsXReposicion
        }]
    });


    //Esta es la parte de los porcentajes de los aviso por Otras Formas de pago
    $('#graficoOtrasFormasDePago').highcharts({
        chart: {
            type: 'pie',
            options3d: {
                enabled: true,
                alpha: 45,
                beta: 0
            }
        },
        //options : highchartsOptions,

        title: {
            text: 'Representacion Grafica de Centimetros Vendidos por Otras Formas de Pago discriminado por Tipo de Aviso'
        },
        tooltip: {
            pointFormat: '{series.name}: <b>{point.percentage:.1f}%</b>'
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                depth: 35,
                dataLabels: {
                    enabled: true,
                    format: '{point.name}'
                }
            }
        },
        series: [{
            type: 'pie',
            name: 'Porcentaje',
            data: dataCmsXOtrasFormasDePago
        }]
    });


});
