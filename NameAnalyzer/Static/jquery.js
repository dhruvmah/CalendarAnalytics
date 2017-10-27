$(function() {

	function getRollUps() {
	  $.getJSON($SCRIPT_ROOT + '/api/rollups', function(data) {
		load_rollups(data);
	  })
	};

	function load_rollups(data) {
        console.log(data);
	  $(".timeInMeetings").append(roundHalf(data["oneMonth"]["timeInMeetings"]) + " hours");
	  $(".numberOfMeetings").append(data["oneMonth"]["numberOfMeetings"] + " meetings");
	  $(".totalPeopleMet").append(data["oneMonth"]["totalPeopleMet"] + " people");
	  for(var i = 0, size = data["oneMonth"]["topFive"].length; i < size; i++){
		  $(".topFive").append("<li>" + "<a href="+ $SCRIPT_ROOT + "/individual/" + data["oneMonth"]["topFive"][i].email + ">" + data["oneMonth"]["topFive"][i].name + "</a></li>");
	  }
	}
	var myBarChart = null;
	getRollUps();
	function fetchData(minDate, maxDate, filter) {
	  $.getJSON($SCRIPT_ROOT + '/api/timespent', {
		minDate: minDate,
		maxDate: maxDate,
		sizeFilter : filter
	  }, function(data) {
		console.log(data);
		draw_overall_chart(data);
	  });
	}


	/*function fetchDates() { 
	  minDate = $("#from").datepicker( "getDate" );
	  maxDate =  $("#to").datepicker( "getDate" );
	  console.log(minDate);
	  console.log(maxDate);
	  var dict = {"minDate" : minDate, "maxDate" : maxDate};
	  return dict;
	  };
	*/
	function fetchDates() { 
	   var radioValue = $("input[name='date_range']:checked").val();
	   var maxDate = new Date();
	   var minDate = new Date();
	   if (radioValue == 3) {
		  minDate.setMonth(minDate.getMonth() - 6);   
	   } else if (radioValue == 2) {
		  minDate.setMonth(minDate.getMonth() - 3);   
	   } else {
		  minDate.setDate(minDate.getMonth() - 1);   
	   }
		var dict = {"minDate": minDate, "maxDate": maxDate};
		return dict; 
	  };

	  function addMonths(date, months) {
		var result = new Date(date),
			expectedMonth = ((date.getMonth() + months) % 12 + 12) % 12;
		result.setMonth(result.getMonth() + months);
		if (result.getMonth() !== expectedMonth) {
		  result.setDate(0);
		}
		return result;
	  }

	function fetchMeetingFilter() { 
	   var radioValue = $("input[name='radio']:checked").val();
	   console.log(radioValue);
	   return radioValue;
	  };

	function getDate( element ) {
	  var date;
	  try {
		  date = $.datepicker.parseDate( dateFormat, element.value );
	  } catch( error ) {
		  date = null;
	  }
		  return date;
	  }


	function fetchData(minDate, maxDate, filter) {
	  $.getJSON($SCRIPT_ROOT + '/api/timespent', {
		minDate: minDate,
		maxDate: maxDate,
		sizeFilter : filter
	  }, function(data) {
		console.log(data);
		draw_overall_chart(data);
	  });
	}

	function roundHalf(num) {
    	return Math.round(num*4)/4;
	}
	

	function draw_overall_chart(data) {
		$("canvas#chart").remove();
		$(".chartContainer").append('<canvas id="chart" class="animated fadeIn" height="150"></canvas>');
		// bar chart data
		var label_array = [];
		var email_array = []
		var one_month_data = [];
		var six_month_data = [];
		var person;

		for(var i = 0, size = data.length; i < size ; i++){
		  person = data[i];
		  console.log(person["displayName"]);
		  label_array.push(person["displayName"]);
		  email_array.push(person["email"]);
		  one_month_data.push(roundHalf(person["oneMonthData"]));
		}

		dataset_array = [
			{
				label: "Average hours per month",
				data: one_month_data
			}
/*			{
				label: "6 month average",
				backgroundColor: "red",
				data: six_month_data
			}
			*/
		]
	   var barData = {
		 labels : label_array,
		 emails: email_array,
		 datasets : dataset_array,
	   } 
	   // get bar chart canvas
	   var mychart = document.getElementById("chart").getContext("2d");
	   steps = 10
	   max = 10
	   // draw bar chart

	  	myBarChart = new Chart(mychart, {
		 	type: 'horizontalBar',
		 	data: barData,
		 	options: {
				barThickness: 20,
				onClick: event['click'],
				title: {
					display: true,
					text: 'Time spent per person',
					padding: 5,
					fontFamily: "BlinkMacSystemFont",
					fontSize: 20,
					fontStyle: "normal"
				  },
				  legend: {
					 position: "bottom"
				  },
				  barValueSpacing: 100,
				  scales: {
					yAxes: [
				  	{
						ticks: {
					   		min: 0,
						}
				  	}]
			  	}
			}
		});
		
	  	//things to do on load of individual page

		//things to do on load of the main page


		$("#chart").click(function(e) {
			var activeBars = myBarChart.getElementAtEvent(e); 
			console.log(activeBars[0]._model.label);

			var a = activeBars[0]._chart.config.data.labels.indexOf(activeBars[0]._model.label);
	   		window.location.href='/individual/' + activeBars[0]._chart.config.data.emails[a];
		});
	  }


		$( ".btn-group" ).click(function() {
		  console.log("Submit button clicked");
		  dates = fetchDates();
		  filter = fetchMeetingFilter()
		  data = fetchData(dates.minDate, dates.maxDate, filter);
		});
})


