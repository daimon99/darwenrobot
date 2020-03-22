var img1 = "static/PlayStation-DualShock-4.jpg"

window.onload = function () {
    var canvas = document.getElementById("c1")
    ctx = canvas.getContext('2d')
    width = canvas.width
    height = canvas.height

    windowWidth = document.body.offsetWidth
    windowHeight = document.body.offsetHeight

    document.addEventListener('mousemove', function(e){
        console.log('hi')
        log(`width: ${windowWidth}, height: ${windowHeight}, X: ${e.clientX}(${e.clientX/windowWidth}), Y: ${e.clientY}(${e.clientY/windowHeight})`)
    })


    ctx.imageSmoothingEnabled = false
    img1 = new Image()
    img1.src = "static/PlayStation-DualShock-4.jpg"
    img1.height = height
    img1.width = width

    img1.onload = function () {
        ctx.drawImage(img1, 0, 0, width, height)
    }
    console.log(ctx)
    log('nihao')

    up = {
        xMin: 0.17,
        xMax: 0.22,
        yMin: 0,217,
        yMax: 0.275
    }
    down = {

    }
}


function log(msg){
    document.getElementById('msg').innerText = msg;
}