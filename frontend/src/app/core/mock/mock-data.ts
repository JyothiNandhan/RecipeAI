import { Recipe } from '../../models/recipe.model';

export const mockRecipes: Recipe[] = [
  {
    title: 'Spicy Garlic Tofu Stir-fry',
    emoji: '🌶️',
    time: 20,
    servings: 2,
    calories: 350,
    ingredients: ['Tofu', 'Garlic', 'Soy Sauce', 'Chili Flakes', 'Broccoli', 'Sesame Oil'],
    steps: [
      'Press and cube the tofu.',
      'Pan-fry tofu until crispy.',
      'Sauté garlic and chili flakes in sesame oil.',
      'Add broccoli and stir-fry for 3 minutes.',
      'Toss everything with soy sauce and serve.'
    ],
    tags: ['Vegan', 'Spicy', 'Asian'],
    description: 'A quick, fiery, and protein-packed vegan stir-fry perfect for a weeknight dinner.',
    match_reason: 'Matches your preference for spicy and vegan meals under 30 minutes.'
  },
  {
    title: 'Creamy Mushroom Risotto',
    emoji: '🍄',
    time: 45,
    servings: 4,
    calories: 420,
    ingredients: ['Arborio Rice', 'Mushrooms', 'Vegetable Broth', 'Parmesan', 'Onion', 'White Wine'],
    steps: [
      'Sauté onions and mushrooms until soft.',
      'Toast the arborio rice for 2 minutes.',
      'Deglaze with white wine.',
      'Gradually add warm broth, stirring constantly until absorbed.',
      'Stir in parmesan and serve hot.'
    ],
    tags: ['Vegetarian', 'Italian', 'Comfort Food'],
    description: 'Rich, creamy, and deeply comforting Italian classic made with earthy mushrooms.',
    match_reason: 'You have mushrooms in your fridge that need to be used up.'
  },
  {
    title: 'Mediterranean Quinoa Salad',
    emoji: '🥗',
    time: 15,
    servings: 3,
    calories: 280,
    ingredients: ['Quinoa', 'Cucumber', 'Cherry Tomatoes', 'Feta Cheese', 'Kalamata Olives', 'Lemon Dressing'],
    steps: [
      'Cook and cool the quinoa.',
      'Chop cucumber and halve the cherry tomatoes.',
      'Mix quinoa, veggies, olives, and crumbled feta.',
      'Toss with lemon dressing before serving.'
    ],
    tags: ['Healthy', 'Gluten-Free', 'Mediterranean'],
    description: 'A light and refreshing salad bursting with Mediterranean flavors.',
    match_reason: 'Perfect for your goal of eating more fresh vegetables.'
  },
  {
    title: 'Classic Beef Burger',
    emoji: '🍔',
    time: 25,
    servings: 2,
    calories: 650,
    ingredients: ['Ground Beef', 'Burger Buns', 'Cheddar Cheese', 'Lettuce', 'Tomato', 'Pickles'],
    steps: [
      'Form ground beef into patties and season with salt and pepper.',
      'Grill or pan-fry patties to desired doneness.',
      'Add cheese in the last minute of cooking.',
      'Toast the buns and assemble the burger with toppings.'
    ],
    tags: ['American', 'High Protein'],
    description: 'A juicy, classic American cheeseburger with all the traditional fixings.',
    match_reason: 'A hearty meal for your weekend cheat day.'
  },
  {
    title: 'Mango Coconut Smoothie Bowl',
    emoji: '🥭',
    time: 10,
    servings: 1,
    calories: 310,
    ingredients: ['Frozen Mango', 'Coconut Milk', 'Banana', 'Chia Seeds', 'Granola'],
    steps: [
      'Blend frozen mango, banana, and coconut milk until smooth.',
      'Pour into a bowl.',
      'Top with chia seeds, granola, and fresh fruit slices.'
    ],
    tags: ['Breakfast', 'Vegan', 'Sweet'],
    description: 'A tropical, refreshing, and photogenic smoothie bowl to start your day.',
    match_reason: 'Matches your request for a quick, sweet breakfast.'
  },
  {
    title: 'Lemon Herb Grilled Chicken',
    emoji: '🍗',
    time: 30,
    servings: 4,
    calories: 380,
    ingredients: ['Chicken Breast', 'Lemon Juice', 'Olive Oil', 'Rosemary', 'Thyme', 'Garlic'],
    steps: [
      'Whisk lemon juice, olive oil, minced garlic, and herbs to make a marinade.',
      'Marinate chicken breasts for at least 20 minutes.',
      'Grill the chicken for 6-8 minutes per side until fully cooked.',
      'Rest for 5 minutes before slicing.'
    ],
    tags: ['Keto', 'High Protein', 'Gluten-Free'],
    description: 'Simple, zesty, and tender grilled chicken breasts loaded with fresh herb flavor.',
    match_reason: 'Ideal for your high-protein, low-carb diet plan.'
  }
];
