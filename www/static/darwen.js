var img1 = "static/PlayStation-DualShock-4.jpg"
var ctx;
window.onload = function () {
    var canvas = document.getElementById("c1")
    width = canvas.width
    height = canvas.height

    windowWidth = document.body.offsetWidth
    windowHeight = document.body.offsetHeight

    document.addEventListener('mousemove', function (e) {
        console.log('hi')
        log(`width: ${windowWidth}, height: ${windowHeight}, X: ${e.clientX}(${e.clientX / windowWidth}), Y: ${e.clientY}(${e.clientY / windowHeight})`)
        drawOther(ctx, e.clientX, e.clientY, 30)
    })

    ctx = drawBackground()
    // drawOther(ctx)
    let up = {
        center: [0.196, 0.235],
        radius: 0.035
    }
    let down = {}
    let left = {}
    let right = {}
    let cameraUp = {}
    let cameraDown = {}
    let liftUp = {}
    let liftDown = {}
}


function log(msg) {
    document.getElementById('msg').innerText = msg;
}

function drawBackground() {
    var canvas = document.getElementById("c1")
    ctx = canvas.getContext('2d')

    ctx.imageSmoothingEnabled = true
    img1 = new Image()
    img1.src = "static/PlayStation-DualShock-4.jpg"
    img1.height = height
    img1.width = width
    img1.onload = function () {
        ctx.drawImage(img1, 0, 0, width, height)
    }
    return ctx
}

function drawOther(ctx, x, y, radius) {
    // ctx.clearRect(0, 0, canvas.width, canvas.height)
    console.log('draw', x, y, radius)
    ctx.strokeStyle = 'orange'
    ctx.beginPath()
    ctx.moveTo(x, y)
    ctx.arc(x, y, radius, 0, Math.PI * 2, false)
    ctx.stroke()
}