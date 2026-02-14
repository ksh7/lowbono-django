document.addEventListener("DOMContentLoaded", function () {
    var eventSelect = document.getElementById("id_event_type");

    function showHideDiv() {

      var divs = document.querySelectorAll("div[id^='emailevent']");
      divs.forEach(function (div) {
          div.style.display = "none";
      });

      var selectedOption = eventSelect.options[eventSelect.selectedIndex].value;
      var selectedDiv = document.getElementById(selectedOption + '-group');
      if (selectedDiv) {
        selectedDiv.style.display = "block";
      }
    }

    eventSelect.addEventListener("change", showHideDiv);
    showHideDiv();
});
