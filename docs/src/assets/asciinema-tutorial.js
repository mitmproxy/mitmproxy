var timer;

function playEvent(e) {
    var player = this;
    timer = setInterval(function(){
        updateInstructions(player);
    }, 250);
}

function pauseEvent(e) {
    if (timer){
        clearInterval(timer);
    }
}

function updateInstructions(player) {
   var instructions = player.instructions;
   var currTime = player.currentTime;
    for(let i = 0; i < instructions.length; i++) {
        if (instructions[i].getAttribute("data-from") < currTime
            && instructions[i].getAttribute("data-to") > currTime) {
            instructions[i].classList.add("is-active");
        }
        else {
            instructions[i].classList.remove("is-active");
        }
    }
}

document.addEventListener("DOMContentLoaded", function() {
    var asciinemaPlayer = document.getElementById('asciinema-player');
    asciinemaPlayer.instructions = asciinemaPlayer.parentElement.getElementsByClassName("panel-block");
    asciinemaPlayer.addEventListener("play", playEvent);
    asciinemaPlayer.addEventListener('pause', pauseEvent);

    for(let i = 0; i < asciinemaPlayer.instructions.length; i++) {
        var instruction = asciinemaPlayer.instructions[i];
        instruction.addEventListener("click", function(e){
            asciinemaPlayer.currentTime = this.getAttribute("data-from");
            asciinemaPlayer.play();
            e.preventDefault();
            return false;
        });
    }
});
