// Auto-dismiss messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        document.querySelectorAll('.alert').forEach(function(el) {
            el.style.opacity = '0';
            el.style.transition = 'opacity 0.5s';
            setTimeout(() => el.remove(), 500);
        });
    }, 5000);
});
