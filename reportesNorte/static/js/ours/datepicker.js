


/*
//$(function() {
  //      $( "#id_fechaDesde" ).datepicker();



    //    $( "#id_fechaHasta" ).datepicker({
	//	minDate: ($( "#id_fechaDesde" ).val()),     //"-20D",
    //    maxDate: "+1M, -1D"
	//    });


//});
*/

// Traducción al español
$(function($){
    $.datepicker.regional['es'] = {
        closeText: 'Cerrar',
        prevText: '<Ant',
        nextText: 'Sig>',
        currentText: 'Hoy',
        monthNames: ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'],
        monthNamesShort: ['Ene','Feb','Mar','Abr', 'May','Jun','Jul','Ago','Sep', 'Oct','Nov','Dic'],
        dayNames: ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'],
        dayNamesShort: ['Dom','Lun','Mar','Mié','Juv','Vie','Sáb'],
        dayNamesMin: ['Do','Lu','Ma','Mi','Ju','Vi','Sá'],
        weekHeader: 'Sm',
        dateFormat: 'dd/mm/yy',
        firstDay: 1,
        isRTL: false,
        showMonthAfterYear: false,
        yearSuffix: ''
    };
    $.datepicker.setDefaults($.datepicker.regional['es']);
});

$('#id_fechaHasta').datepicker({

    onSelect: function() {


    },
    onClose: function() {
        $(this).focus();
    },
    dateFormat:'dd/mm/yy'
});

$('#id_fechaDesde').datepicker({

    onSelect: function(dateText, inst) {
        //var nyd = new Date($('#id_fechaDesde').val());

        var fecha = $('#id_fechaDesde').val();
        var dia = fecha.substring(0,2);
        var mes = fecha.substring(3,5);
        var anio = fecha.substring(6,10);


        var fechaIng = mes + '/' +dia + '/'+anio;


        var nyd2 = new Date(fechaIng);
        // se hace esto para crear una fecha a partir de una fecha en ingles ya que nosotros utilizamos dd/mm/aa y ellos utilizan mm/dd/yy
        var mesN = (nyd2.getMonth() + 2) ; //Es mas 2 porque Enero en ingles es 0 al transformar y como se necesita
                                           // que sea un mes mas para el rango, se pone +2. Ej. Enero = 0, si se quiere
                                           // que sea de Enero a Febrero se coloca así: mesNuevo = 0 + 2 (ya que despues
                                           //se transforma a español y nuestros inputs estan en ese idioma: Enero = 1 y febrero = 2)


        var fechaAux = mesN + '/' + dia + '/'+anio;

        var nyd = new Date(fechaAux);

        console.log(nyd2);

        nyd.setDate(nyd.getDate() - 1);


        $('#id_fechaHasta').datepicker("option", {
            minDate: nyd2,
            maxDate: nyd
        });


    },
    onClose: function() {
        $(this).focus();
    },
    dateFormat:'dd/mm/yy'
});