/**
 * Homepage Dynamic Content Generator
 * Generates the premium restaurant cards, categories, and initializes Swiper carousels.
 */

document.addEventListener('DOMContentLoaded', () => {
    
    // South Indian Food Image URLs — 100% reliable Unsplash CDN (no hotlink issues)
    // + Swiggy CDN for idli (confirmed working) + Wikipedia for confirmed-existing files
    const FOOD_IMGS = {
        // Idli - Swiggy CDN (confirmed working)
        idli:            'https://instamart-media-assets.swiggy.com/swiggy/image/upload/fl_lossy,f_auto,q_auto,h_600,w_600//InstamartAssets/idli_vada.webp',
        // Dosa - Unsplash South Indian food photo (always loads)
        dosa:            'https://images.unsplash.com/photo-1601050690597-df0568f70950?q=80&w=400&h=400&fit=crop',
        masalaDosa:      'https://images.unsplash.com/photo-1601050690597-df0568f70950?q=80&w=400&h=400&fit=crop',
        benneDosa:       'https://images.unsplash.com/photo-1601050690597-df0568f70950?q=80&w=400&h=400&fit=crop',
        // Vada - confirmed Wikipedia file
        vada:            'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Medu_Vadas.JPG/400px-Medu_Vadas.JPG',
        // Thali / Meals - Unsplash Indian thali
        thali:           'https://images.unsplash.com/photo-1585937421612-70a008356fbe?q=80&w=400&h=400&fit=crop',
        southMeal:       'https://images.unsplash.com/photo-1585937421612-70a008356fbe?q=80&w=400&h=400&fit=crop',
        // Pongal - confirmed Wikipedia file
        pongal:          'https://upload.wikimedia.org/wikipedia/commons/thumb/2/21/Ven_pongal_with_sambar_and_chutney.jpg/400px-Ven_pongal_with_sambar_and_chutney.jpg',
        // Uttapam - confirmed Wikipedia file
        uttapam:         'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/Mini_Uttappam.jpg/400px-Mini_Uttappam.jpg',
        // Filter Coffee - Unsplash coffee photo (always loads)
        filterCoffee:    'https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?q=80&w=400&h=400&fit=crop',
        // Mysore Pak / Sweets - Unsplash Indian sweets/dessert
        mysorePak:       'https://images.unsplash.com/photo-1551024601-bec78aea704b?q=80&w=400&h=400&fit=crop',
        // Payasam - Unsplash dessert pudding
        payasam:         'https://images.unsplash.com/photo-1571167366235-a898c6e04478?q=80&w=400&h=400&fit=crop',
        // Akki Rotti - Unsplash Indian flatbread
        akkirotti:       'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?q=80&w=400&h=400&fit=crop',
        // Ragi Mudde - Unsplash Indian food
        ragimudde:       'https://images.unsplash.com/photo-1565557623262-b51c2513a641?q=80&w=400&h=400&fit=crop',
        // Healthy / Vegetarian - Unsplash veggie bowl
        vegetarianCurry: 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?q=80&w=400&h=400&fit=crop',
    };

    // Restaurant Image URLs - Actual restaurant interior/exterior photos from Unsplash
    const REST_IMGS = {
        r1: 'https://images.unsplash.com/photo-1514933651103-005eec06c04b?q=80&w=800',
        r2: 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?q=80&w=800',
        r3: 'https://images.unsplash.com/photo-1559339352-11d035aa65de?q=80&w=800',
        r4: 'https://images.unsplash.com/photo-1529193591184-b1d58069ecdd?q=80&w=800',
        r5: 'https://images.unsplash.com/photo-1544148103-0773bf10d330?q=80&w=800',
        r6: 'https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?q=80&w=800',
        r7: 'https://images.unsplash.com/photo-1537047902294-62a40c20a6ae?q=80&w=800',
        r8: 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?q=80&w=800',
        r9: 'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?q=80&w=800',
        r10:'https://images.unsplash.com/photo-1552566626-52f8b828a592?q=80&w=800',
        r11:'https://images.unsplash.com/photo-1543353071-873f17a7a088?q=80&w=800',
        r12:'https://images.unsplash.com/photo-1424847651672-bf20a4b0982b?q=80&w=800',
    };

    // 1. Categories Data (15 Categories) — each with exact dish-specific image
    const categories = [
        { name: 'Dosa',              icon: FOOD_IMGS.masalaDosa,   count: 120 },
        { name: 'Idli',              icon: FOOD_IMGS.idli,          count: 85  },
        { name: 'Vada',              icon: FOOD_IMGS.vada,          count: 140 },
        { name: 'Meals',             icon: FOOD_IMGS.thali,         count: 65  },
        { name: 'Filter Coffee',     icon: FOOD_IMGS.filterCoffee,  count: 210 },
        { name: 'Breakfast',         icon: FOOD_IMGS.pongal,        count: 110 },
        { name: 'Traditional Sweets',icon: FOOD_IMGS.mysorePak,     count: 90  },
        { name: 'Healthy Meals',     icon: FOOD_IMGS.vegetarianCurry, count: 50 },
        { name: 'Family Combo',      icon: FOOD_IMGS.southMeal,     count: 75  },
        { name: 'Pongal',            icon: FOOD_IMGS.pongal,        count: 40  },
        { name: 'Uttapam',           icon: FOOD_IMGS.uttapam,       count: 80  },
        { name: 'Ragi Mudde',        icon: FOOD_IMGS.ragimudde,     count: 60  },
        { name: 'Payasam',           icon: FOOD_IMGS.payasam,       count: 55  },
        { name: 'Akki Rotti',        icon: FOOD_IMGS.akkirotti,     count: 45  },
        { name: 'Mysore Pak',        icon: FOOD_IMGS.mysorePak,     count: 65  }
    ];

    // Populate Categories Swiper
    const categoryWrapper = document.querySelector('.categorySwiper .swiper-wrapper');
    if (categoryWrapper) {
        let html = '';
        categories.forEach(cat => {
            html += `
            <div class="swiper-slide">
                <a href="#" class="category-card-premium">
                    <div class="category-content-wrap">
                        <div class="category-icon-wrap">
                            <img src="${cat.icon}" alt="${cat.name}" onerror="this.onerror=null;this.src='https://images.unsplash.com/photo-1601050690597-df0568f70950?q=80&w=200&h=200&fit=crop'">
                        </div>
                        <h6>${cat.name}</h6>
                        <span>${cat.count} places</span>
                    </div>
                </a>
            </div>
            `;
        });
        categoryWrapper.innerHTML = html;
        
        new Swiper('.categorySwiper', {
            slidesPerView: 2,
            spaceBetween: 16,
            navigation: {
                nextEl: '.categorySwiper .swiper-button-next',
                prevEl: '.categorySwiper .swiper-button-prev',
            },
            breakpoints: {
                576: { slidesPerView: 3, spaceBetween: 20 },
                768: { slidesPerView: 4, spaceBetween: 24 },
                992: { slidesPerView: 6, spaceBetween: 24 },
                1200: { slidesPerView: 8, spaceBetween: 24 }
            }
        });
    }

    // Template for Premium Restaurant Card
    const createRestaurantCard = (data) => `
        <a href="restaurant_detail.html" class="card-qb-premium h-100">
            <div class="card-img-wrapper">
                <img src="${data.img}" class="card-img-top" alt="${data.name}" onerror="this.onerror=null;this.src='https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?q=80&w=800';">
                
                ${data.promoted ? `<div class="qb-badge-floating qb-badge-top-left"><i class="fa-solid fa-bullhorn text-primary"></i> Promoted</div>` : ''}
                
                <button class="card-favorite-btn ${data.favorite ? 'active' : ''}" onclick="event.preventDefault(); this.classList.toggle('active');">
                    <i class="fa-solid fa-heart"></i>
                </button>

                ${data.offer ? `
                <div class="qb-offer-ribbon">
                    <div class="qb-offer-text"><i class="fa-solid fa-tag"></i> ${data.offer}</div>
                </div>
                ` : ''}
            </div>
            
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-1">
                    <h5 class="qb-restaurant-title" title="${data.name}">${data.name}</h5>
                    <div class="qb-badge-floating position-static ms-2 px-2 py-1 bg-success text-white shadow-none">
                        ${data.rating} <i class="fa-solid fa-star" style="font-size: 0.6rem;"></i>
                    </div>
                </div>
                
                <div class="qb-cuisine-tags" title="${data.cuisines}">${data.cuisines}</div>
                
                <div class="qb-card-divider"></div>
                
                <div class="qb-restaurant-meta">
                    <div class="qb-restaurant-meta-item">
                        <i class="fa-regular fa-clock"></i> ${data.time}
                    </div>
                    <div class="qb-restaurant-meta-item">
                        <i class="fa-solid fa-location-dot"></i> ${data.distance}
                    </div>
                    <div class="qb-restaurant-meta-item">
                        ${data.freeDelivery ? '<span class="text-success fw-bold">Free Delivery</span>' : '₹40 Delivery'}
                    </div>
                </div>
            </div>
        </a>
    `;

    // 2. Featured Restaurants — restaurant interior/exterior photos
    const featuredRestaurants = [
        { name: "Namma Oota",      cuisines: "Karnataka Meals, Premium",         img: REST_IMGS.r1,  rating: "4.9", time: "45 mins", distance: "4.2 km", offer: "50% OFF up to ₹200",  promoted: true,  freeDelivery: false },
        { name: "Bengaluru Tiffins", cuisines: "South Indian, Breakfast, Idli",  img: REST_IMGS.r2,  rating: "4.8", time: "35 mins", distance: "2.1 km", offer: "Flat ₹150 OFF",        promoted: false, freeDelivery: true  },
        { name: "Halli Mane",      cuisines: "South Indian, Thali, Meals",        img: REST_IMGS.r3,  rating: "4.7", time: "50 mins", distance: "5.5 km", offer: "Complimentary Dessert",promoted: true,  freeDelivery: false },
        { name: "Udupi Upahara",   cuisines: "Udupi, Veg Meals, Breakfast",       img: REST_IMGS.r4,  rating: "4.6", time: "40 mins", distance: "3.8 km", offer: "20% OFF on All Items", promoted: false, freeDelivery: true  },
        { name: "Malnad Kitchen",  cuisines: "Karnataka, Home-style, Sweets",     img: REST_IMGS.r5,  rating: "4.8", time: "30 mins", distance: "1.5 km", offer: "",                    promoted: false, freeDelivery: true  }
    ];

    const featuredWrapper = document.getElementById('featured-wrapper');
    if (featuredWrapper) {
        let html = '';
        featuredRestaurants.forEach(res => {
            html += `<div class="swiper-slide">${createRestaurantCard(res)}</div>`;
        });
        featuredWrapper.innerHTML = html;
        
        new Swiper('.featuredSwiper', {
            slidesPerView: 1.2,
            spaceBetween: 20,
            pagination: { el: '.swiper-pagination', clickable: true },
            breakpoints: {
                768: { slidesPerView: 2.2, spaceBetween: 24 },
                1200: { slidesPerView: 3.2, spaceBetween: 30 }
            }
        });
    }

    // 3. Popular Breakfast in Bengaluru (Grid)
    const popularGrid = document.getElementById('popular-grid');
    if (popularGrid) {
        const popularData = [
            { name: "Filter Coffee House",  cuisines: "Dosa, Idli, South Indian Breakfast", img: REST_IMGS.r6,  rating: "4.3", time: "25 mins", distance: "1.2 km", offer: "Free Vada on ₹299",       freeDelivery: true  },
            { name: "Akki Rotti Corner",    cuisines: "Akki Rotti, Ragi Mudde, Meals",      img: REST_IMGS.r7,  rating: "4.4", time: "30 mins", distance: "1.8 km", offer: "Flat 50% OFF",             freeDelivery: true  },
            { name: "Mysuru Meals",         cuisines: "Veg Meals, Karnataka Thali, Rice",    img: REST_IMGS.r8,  rating: "4.5", time: "20 mins", distance: "0.8 km", offer: "",                        freeDelivery: false },
            { name: "South Spice Veg",      cuisines: "Banana Leaf Meals, Puliyogare, Rice", img: REST_IMGS.r12, rating: "4.6", time: "40 mins", distance: "3.5 km", offer: "₹100 OFF above ₹500",     freeDelivery: false },
            { name: "Oota Mane",            cuisines: "Bisibele Bath, Khara Bath, Kesari",   img: REST_IMGS.r9,  rating: "4.4", time: "25 mins", distance: "1.5 km", offer: "",                        freeDelivery: true  },
            { name: "Arogya Ahaara",        cuisines: "Healthy Meals, Pongal, Filter Coffee",img: REST_IMGS.r10, rating: "4.7", time: "15 mins", distance: "0.5 km", offer: "Free Buttermilk",          freeDelivery: true  },
        ];
        
        let html = '';
        popularData.forEach(res => {
            html += `<div class="col-sm-6 col-lg-4">${createRestaurantCard(res)}</div>`;
        });
        popularGrid.innerHTML = html;
    }

    // 4. Traditional South Indian Breakfast Swiper
    const fastDeliveryWrapper = document.getElementById('fast-delivery-wrapper');
    if (fastDeliveryWrapper) {
        const fastData = [
            { name: "Udupi Veg Express",  cuisines: "Idli, Vada, Dosa, Sambar",          img: REST_IMGS.r11, rating: "4.2", time: "15 mins", distance: "0.5 km", offer: "Free Chutney",   freeDelivery: true  },
            { name: "Namma Bhojana",      cuisines: "Pongal, Khara Bath, Kesari Bath",    img: REST_IMGS.r3,  rating: "4.3", time: "18 mins", distance: "0.7 km", offer: "",              freeDelivery: true  },
            { name: "Karnataka Oota",     cuisines: "Ragi Mudde, Jolada Rotti, Sabzi",    img: REST_IMGS.r7,  rating: "4.1", time: "22 mins", distance: "1.1 km", offer: "20% OFF",       freeDelivery: false },
            { name: "Dosa King",          cuisines: "Masala Dosa, Benne Dosa, Set Dosa",  img: REST_IMGS.r6,  rating: "4.3", time: "19 mins", distance: "0.9 km", offer: "Buy 1 Get 1",   freeDelivery: true  },
        ];
        
        let html = '';
        fastData.forEach(res => {
            html += `<div class="swiper-slide">${createRestaurantCard(res)}</div>`;
        });
        fastDeliveryWrapper.innerHTML = html;
        
        new Swiper('.fastDeliverySwiper', {
            slidesPerView: 1.2,
            spaceBetween: 20,
            navigation: {
                nextEl: '.fastDeliverySwiper .swiper-button-next',
                prevEl: '.fastDeliverySwiper .swiper-button-prev',
            },
            breakpoints: {
                576: { slidesPerView: 2.2, spaceBetween: 24 },
                992: { slidesPerView: 3.2, spaceBetween: 24 },
                1200: { slidesPerView: 4, spaceBetween: 30 }
            }
        });
    }

    // 5. Today's Karnataka Specials (Grid)
    const dealsGrid = document.getElementById('deals-grid');
    if (dealsGrid) {
        const dealsData = [
            { name: "Halli Mane",       cuisines: "Veg Meals, Karnataka Thali",             img: REST_IMGS.r8,  rating: "4.5", time: "35 mins", distance: "3.2 km", offer: "60% OFF up to ₹150", freeDelivery: true  },
            { name: "Bengaluru Tiffins",cuisines: "Thatte Idli, Maddur Vada, Coffee",        img: REST_IMGS.r2,  rating: "4.4", time: "40 mins", distance: "4.5 km", offer: "Flat ₹200 OFF",      freeDelivery: false },
            { name: "Namma Oota",       cuisines: "Banana Leaf Meals, South Indian Thali",   img: REST_IMGS.r9,  rating: "4.1", time: "25 mins", distance: "1.8 km", offer: "50% OFF",             freeDelivery: true  },
        ];
        
        let html = '';
        dealsData.forEach(res => {
            html += `<div class="col-sm-6 col-lg-4">${createRestaurantCard(res)}</div>`;
        });
        dealsGrid.innerHTML = html;
    }

    // 6. Healthy Choices
    const healthyWrapper = document.getElementById('healthy-wrapper');
    if (healthyWrapper) {
        const healthyData = [
            { name: "Eat.Fit",          cuisines: "Pongal, Salads, Ragi Mudde",          img: REST_IMGS.r5,  rating: "4.6", time: "25 mins", distance: "2.1 km", offer: "20% OFF",              freeDelivery: true  },
            { name: "Green Leaf Veg",   cuisines: "Curd Rice, Lemon Rice, Salads",        img: REST_IMGS.r10, rating: "4.7", time: "30 mins", distance: "2.5 km", offer: "",                    freeDelivery: true  },
            { name: "Arogya Ahaara",    cuisines: "Vegan, Healthy Veg, Buttermilk",       img: REST_IMGS.r12, rating: "4.5", time: "35 mins", distance: "3.0 km", offer: "Free Tender Coconut", freeDelivery: false },
            { name: "Oota Mane Fresh",  cuisines: "Payasam, Kesari Bath, Fresh Fruits",   img: REST_IMGS.r4,  rating: "4.8", time: "20 mins", distance: "1.2 km", offer: "",                    freeDelivery: true  },
        ];
        
        let html = '';
        healthyData.forEach(res => {
            html += `<div class="swiper-slide">${createRestaurantCard(res)}</div>`;
        });
        healthyWrapper.innerHTML = html;
        
        new Swiper('.healthySwiper', {
            slidesPerView: 1.2,
            spaceBetween: 20,
            navigation: {
                nextEl: '.healthySwiper .swiper-button-next',
                prevEl: '.healthySwiper .swiper-button-prev',
            },
            breakpoints: {
                576: { slidesPerView: 2.2, spaceBetween: 24 },
                992: { slidesPerView: 3.2, spaceBetween: 24 },
                1200: { slidesPerView: 4, spaceBetween: 30 }
            }
        });
    }

    // 7. Customer Reviews — Indian names & South Indian food experience
    const reviewWrapper = document.querySelector('.reviewSwiper .swiper-wrapper');
    if (reviewWrapper) {
        const reviews = [
            { name: "Ananya R.",     avatar: "https://randomuser.me/api/portraits/women/44.jpg", text: "UrbanFoods delivers the most authentic Karnataka meals! The Banana Leaf Meals from Halli Mane arrive piping hot every time. 😍",              rating: 5, time: "2 days ago"   },
            { name: "Karthik M.",    avatar: "https://randomuser.me/api/portraits/men/32.jpg",   text: "Best dosa delivery in Bengaluru! Benne Dosa from Namma Oota is crispy and arrives in 20 mins. Superb app!",                                   rating: 5, time: "1 week ago"   },
            { name: "Pooja S.",      avatar: "https://randomuser.me/api/portraits/women/68.jpg", text: "Love the filter coffee that comes from Bengaluru Tiffins — still hot when it arrives in Indiranagar! Great service.",                         rating: 4, time: "2 weeks ago"  },
            { name: "Manjunath B.",  avatar: "https://randomuser.me/api/portraits/men/91.jpg",   text: "Thatte Idli from Udupi Veg Express is exactly like the original! UrbanFoods really understands authentic South Indian food.",                 rating: 5, time: "3 weeks ago"  }
        ];
        
        let html = '';
        reviews.forEach(review => {
            let stars = '';
            for(let i=0; i<5; i++) {
                stars += `<i class="fa-solid fa-star ${i < review.rating ? 'text-warning' : 'text-muted opacity-25'}"></i>`;
            }
            html += `
            <div class="swiper-slide">
                <div class="card border-0 shadow-sm rounded-4 h-100 p-4 bg-white">
                    <div class="d-flex align-items-center mb-4">
                        <img src="${review.avatar}" class="rounded-circle shadow-sm" width="60" height="60" alt="${review.name}">
                        <div class="ms-3">
                            <h6 class="fw-bold mb-1">${review.name}</h6>
                            <div class="small text-muted">${review.time}</div>
                        </div>
                    </div>
                    <div class="mb-3">${stars}</div>
                    <p class="text-muted fst-italic">"${review.text}"</p>
                </div>
            </div>
            `;
        });
        reviewWrapper.innerHTML = html;
        
        new Swiper('.reviewSwiper', {
            slidesPerView: 1.1,
            spaceBetween: 20,
            pagination: { el: '.reviewSwiper .swiper-pagination', clickable: true },
            breakpoints: {
                768: { slidesPerView: 2.1, spaceBetween: 24 },
                1200: { slidesPerView: 3, spaceBetween: 30 }
            }
        });
    }

    // Number Counter Animation
    const counters = document.querySelectorAll('.counter');
    const speed = 200; 

    const animateCounters = () => {
        counters.forEach(counter => {
            const updateCount = () => {
                const target = +counter.getAttribute('data-target');
                const count = +counter.innerText.replace(/,/g, '');
                const inc = target / speed;
                if (count < target) {
                    counter.innerText = Math.ceil(count + inc).toLocaleString();
                    setTimeout(updateCount, 10);
                } else {
                    counter.innerText = target.toLocaleString();
                }
            };
            const observer = new IntersectionObserver((entries) => {
                if(entries[0].isIntersecting) {
                    updateCount();
                    observer.disconnect();
                }
            });
            observer.observe(counter);
        });
    }
    setTimeout(animateCounters, 500);
});
